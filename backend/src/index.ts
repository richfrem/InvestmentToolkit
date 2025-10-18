/**
 * Backend Server Entry Point
 *
 * - Loads environment variables
 * - Sets up the Express app and middleware
 * - Registers API routes (including Questrade proxy routes)
 * - Starts the server and listens on the configured port
 *
 * Start this server with:
 *   npm run dev
 * or
 *   ts-node --esm src/index.ts
 */
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
// Delay importing route modules until after dotenv is configured so imported
// modules (like aiService) can read environment variables at module-init time.

// Prefer a repository-root .env (../.env) when running backend from the backend/ folder.
// Fall back to default dotenv behavior if not found.
const rootEnvPath = path.resolve(process.cwd(), '..', '.env');
if (fs.existsSync(rootEnvPath)) {
  dotenv.config({ path: rootEnvPath });
} else {
  dotenv.config();
}

const app = express();
const PORT = process.env.BACKEND_PORT || 3001;

app.use(cors());
app.use(express.json());

// Serve static files from TargetPortfolio directory
app.use('/TargetPortfolio', express.static(path.join(process.cwd(), '..', 'TargetPortfolio')));

// Dynamically import routes now that environment variables are loaded
const questradeRoutes = (await import('./routes/questrade.ts')).default;
app.use('/api', questradeRoutes);

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});

export default app;