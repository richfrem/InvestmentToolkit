// capture_code_snapshot.js (v4.1 - Standardized Path Output)
// This version is updated to correctly handle the new NPM workspace structure
// and recognizes the `.cjs` file extension for our CommonJS backend files.
// The primary change is to ensure all captured file paths in the headers
// are consistently prefixed with './' for easier parsing and consistency.

// Using console.log directly since this is a root-level utility script

import fs from 'fs';
import path from 'path';
// Lightweight token estimate replacement for 'gpt-tokenizer'
// We avoid an external dependency by using a conservative character-based estimate.
function estimateTokenCount(text) {
    // Rough heuristic: ~4 characters per token on average for English text.
    // Use ceiling to avoid undercounting. Add a small multiplier to be conservative.
    if (!text) return 0;
    const chars = text.length;
    return Math.ceil(chars / 4.0 * 1.05);
}

const projectRoot = new URL('.', import.meta.url).pathname;
const distilledOutputFile = path.join(projectRoot, 'all_markdown_and_code_snapshot_llm_distilled.txt');

// --- CONFIGURATION ---
const excludeDirNames = new Set([
    'node_modules', '.next', '.git', '.cache', '.turbo', '.vscode', 'dist', 'build', 'coverage', 'out', 'tmp', 'temp', 'logs', '.idea', '.parcel-cache', '.storybook', '.husky', '.pnpm', '.yarn', '.svelte-kit', '.vercel', '.firebase', '.expo', '.expo-shared',
    '__pycache__', '.ipynb_checkpoints', '.tox', '.eggs', 'eggs', '.venv', 'venv', 'env',
    '.svn', '.hg', '.bzr', 'agents/feedback', 'agents/screenshots', 'playwright-report', 'test-results', 'supabase/.temp'
]);

// Exclude relative paths from the project root.
const excludeRelativePaths = [
    // No top-level paths need to be excluded by default in this project structure.
    // '.github' would be a good example if you had it.
    // Exclude all sensitive data files and folders (matches .gitignore)
    'TargetPortfolio',
    'backend/src/data/accounts.ts',
    'backend/src/data/balances.ts',
    'backend/src/data/currentHoldings.ts',
    'backend/src/data/orders.ts',
    'backend/src/data/positions.ts',
];

const alwaysExcludeFiles = new Set([
    'all_markdown_and_code_snapshot_llm_distilled.txt',
    '.gitignore',
    '.DS_Store',
    '.env',
    'capture_code_snapshot.js',
    'package-lock.json', // Exclude lock files as they are very large and machine-generated
    'pnpm-lock.yaml',
    'yarn.lock'
]);

// THE FIX: Added '.cjs' to the list of allowed extensions.
const allowedExtensions = ['.md', '.js', '.ts', '.tsx', '.sh', '.sql', '.cjs', '.mjs', '.json', '.toml', '.yml', '.yaml'];
// --- END CONFIGURATION ---

const fileSeparatorStart = '--- START OF FILE';
const fileSeparatorEnd = '--- END OF FILE';

function appendFileContent(filePath, basePath) {
    // Ensure relativePath always starts with ./
    const relativePath = './' + path.relative(basePath, filePath).replace(/\\/g, '/');
    let fileContent = '';
    try {
        fileContent = fs.readFileSync(filePath, 'utf8');
    } catch (readError) {
        fileContent = `[Content not captured due to read error: ${readError.message}.]`;
    }

    // --- Sensitive content redaction ---------------------------------
    // Configurable list of environment/key names to redact when found
    const sensitiveKeyNames = [
        'OPENAI_API_KEY',
        'GEMINI_API_KEY',
        'RESEND_API_KEY',
        'RESEND_FROM_EMAIL',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_PHONE_NUMBER',
        'VITE_GOOGLE_MAPS_API_KEY',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_ANON_KEY',
        'PGPASSWORD'
    ];

    // Build a regex that matches assignments like KEY=VALUE or KEY: "value"
    const sensAlt = sensitiveKeyNames.join('|').replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    const keyAssignRegex = new RegExp(`\\b(${sensAlt})\\b\\s*[:=]\\s*['\"]?[^'\"\n\\r]*`, 'gi');

    // Redact bearer tokens and likely long-looking secret tokens (e.g., sk-...)
    const bearerRegex = /Bearer\s+[A-Za-z0-9\-_.]+/gi;
    const longKeyRegex = /\b(sk-[A-Za-z0-9\-_.]{10,})\b/gi;

    // Perform redactions on fileContent; produce sanitized copy for snapshot
    let sanitized = fileContent
        .replace(keyAssignRegex, (m, p1) => `${p1}=[REDACTED]`)
        .replace(bearerRegex, 'Bearer [REDACTED]')
        .replace(longKeyRegex, '[REDACTED_LONG_KEY]');

    // If we redacted anything, annotate the snapshot output for this file
    const redacted = sanitized !== fileContent;

    // Use the standardized relativePath with ./ prefix in the separator
    let output = `${fileSeparatorStart} ${relativePath} ---\n\n`;
    output += sanitized;
    if (redacted) {
        output += `\n\n[NOTE] Sensitive values were detected and redacted in this file.`;
    }
    output += `\n${fileSeparatorEnd} ---\n\n`;
    return output;
}

console.log(`[INFO] Starting project scan from root: ${projectRoot}`);
console.log(`[INFO] Script version: v4.1 (Standardized Path Output)`);

try {
    const fileTreeLines = [];
    let distilledContent = '';
    let filesCaptured = 0;
    let itemsSkipped = 0;

    function traverseAndCapture(currentPath) {
        const baseName = path.basename(currentPath);
        const relativePath = path.relative(projectRoot, currentPath).replace(/\\/g, '/');

        // Rule 1: Exclude entire directories by name (e.g., node_modules)
        if (fs.statSync(currentPath).isDirectory() && excludeDirNames.has(baseName)) {
            itemsSkipped++;
            return;
        }

        // Rule 2: Exclude specific relative paths (e.g., .github)
        for (const excludedPath of excludeRelativePaths) {
            if (relativePath.startsWith(excludedPath)) {
                itemsSkipped++;
                return;
            }
        }

        // If this is a directory, add it to the tree and recurse
        if (fs.statSync(currentPath).isDirectory()) {
            if (relativePath) { // Don't add the root itself to the tree list
                fileTreeLines.push('./' + relativePath + '/');
            }
            const items = fs.readdirSync(currentPath).sort();
            for (const item of items) {
                traverseAndCapture(path.join(currentPath, item));
            }

        // If it's a file, perform exclusion checks first, then add to tree and capture
        } else if (fs.statSync(currentPath).isFile()) {
            // Rule 3: Exclude specific filenames (e.g., .DS_Store)
            if (alwaysExcludeFiles.has(baseName)) {
                itemsSkipped++;
                return;
            }

            // Rule 4: Handle special .env file logic (exclude all real env files, allow .env.example)
            if (baseName.startsWith('.env') && baseName !== '.env.example') {
                itemsSkipped++;
                return;
            }

            // Rule 5: Only include files with allowed extensions
            if (!allowedExtensions.includes(path.extname(baseName).toLowerCase())) {
                itemsSkipped++;
                return;
            }

            // Passed all checks: add to file tree and capture the file content
            if (relativePath) {
                fileTreeLines.push('./' + relativePath);
            }
            distilledContent += appendFileContent(currentPath, projectRoot);
            filesCaptured++;
        }
    }

    traverseAndCapture(projectRoot);

    // The file tree already includes './' from the traverseAndCapture function
    const fileTreeContent = '# Directory Structure (relative to project root)\n' + fileTreeLines.map(line => '  ' + line).join('\n') + '\n\n';

    // --- Forge the final output file ---
    let header = `# All Markdown Files Snapshot (LLM-Distilled)\n\nGenerated On: ${new Date().toISOString()}\n\n{TOKEN_COUNT_PLACEHOLDER}\n\n`;
    const finalContent = header + fileTreeContent + distilledContent;
    const tokenCount = estimateTokenCount(finalContent);
    const finalContentWithToken = finalContent.replace('{TOKEN_COUNT_PLACEHOLDER}', `# Mnemonic Weight (Token Count, estimated): ~${tokenCount.toLocaleString()} tokens`);

    fs.writeFileSync(distilledOutputFile, finalContentWithToken, 'utf8');

    console.log(`\n[SUCCESS] Snapshot successfully generated: ${distilledOutputFile}`);
    console.log(`[METRIC] Total Token Count: ~${tokenCount.toLocaleString()} tokens`);
    console.log(`[STATS] Files Captured: ${filesCaptured} | Directories/Files Skipped: ${itemsSkipped}`);

} catch (err) {
    console.error(`[FATAL] An error occurred during snapshot generation: ${err.message}`);
    console.error(err.stack);
}
