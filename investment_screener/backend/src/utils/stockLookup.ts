/**
 * stockLookup.ts - Fuzzy stock ticker lookup helper.
 * 
 * Purpose:
 *   Builds a dictionary and normalizes search terms to resolve ticker symbols from company names
 *   or search queries (fuzzy matching).
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 * 
 * Functions Index:
 *   - normalizeSearchTerm(term: string) - Normalize search term string
 *   - stripSuffixesStages(normalizedName: string) - Strip common corporate suffixes sequentially, listing each stage
 *   - stripSuffixes(normalizedName: string) - Strip common corporate suffixes to produce a base company name
 *   - buildLookupDictionary(holdings: any[]) - Build a proxy-backed dictionary for resolving fuzzy names
 */

/**
 * Normalize search term string by converting to uppercase, removing punctuation, and trimming.
 * 
 * @param {string} term - Search query or company name
 * @returns {string} Normalized string
 */
export function normalizeSearchTerm(term: string): string {
    /**
     * Replaces standard punctuation characters and spaces with singular blank characters.
     */
    return term
        .toUpperCase()
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, '') // remove punctuation
        .replace(/\s+/g, ' ')                      // normalize whitespace
        .trim();
}

/**
 * Strip common corporate suffixes sequentially, listing each intermediate string stage.
 * 
 * @param {string} normalizedName - Pre-normalized company name
 * @returns {string[]} Mapped stages of suffix stripping
 */
export function stripSuffixesStages(normalizedName: string): string[] {
    /**
     * Loops checking trailing words against suffixes list, popping matches, and collecting stages.
     */
    const suffixes = [
        'INCORPORATED', 'CORPORATION', 'COMMON STOCK', 'CLASS A', 
        'GLOBAL', 'SYSTEMS', 'COMMON', 'CORP', 'INC', 'LTD', 'SYS', 'CO'
    ];
    let words = normalizedName.split(' ');
    const stages: string[] = [normalizedName];
    while (words.length > 1) {
        const lastWord = words[words.length - 1];
        if (suffixes.includes(lastWord)) {
            words.pop();
            stages.push(words.join(' '));
        } else {
            break;
        }
    }
    return stages;
}

/**
 * Strip common corporate suffixes to produce a base company name.
 * 
 * @param {string} normalizedName - Pre-normalized company name
 * @returns {string} Fully stripped company name string
 */
export function stripSuffixes(normalizedName: string): string {
    /**
     * Delegates to stripSuffixesStages and returns the final element.
     */
    const stages = stripSuffixesStages(normalizedName);
    return stages[stages.length - 1];
}

/**
 * Build a proxy-backed dictionary for resolving fuzzy company names to ticker symbols.
 * 
 * @param {any[]} holdings - List of portfolio holdings object entries
 * @returns {Record<string, string>} Proxy-wrapped dictionary map
 */
export function buildLookupDictionary(holdings: any[]): Record<string, string> {
    /**
     * Initializes manual aliases, loops holdings to register names and stages of corporate names,
     * and returns a Proxy intercepting GET lookups to apply name normalization.
     */
    const dict: Record<string, string> = {};

    // 1. Pre-populate manual alias overrides for typos and phonetic matches
    const ALIAS_MAP: Record<string, string> = {
        'CEREBRAS': 'CBRS',
        'CEREBRUS': 'CBRS',
        'CEREBRES': 'CBRS',
        'SEREBRAS': 'CBRS',
        'GOOGLE': 'GOOG',
        'FACEBOOK': 'META',
        'TSMC': 'TSM',
    };

    for (const [alias, ticker] of Object.entries(ALIAS_MAP)) {
        dict[alias] = ticker;
    }

    // 2. Map holdings
    for (const h of holdings) {
        if (!h.ticker) continue;
        const ticker = h.ticker.toUpperCase();
        dict[ticker] = ticker;

        if (h.name) {
            const norm = normalizeSearchTerm(h.name);
            dict[norm] = ticker;

            const stages = stripSuffixesStages(norm);
            for (const stage of stages) {
                dict[stage] = ticker;
            }

            const fullyStripped = stages[stages.length - 1];
            // Also map single-word names if they are reasonably long (e.g. "Alphabet" -> GOOG)
            const firstWord = fullyStripped.split(' ')[0];
            if (firstWord && firstWord.length >= 4) {
                dict[firstWord] = ticker;
            }
        }
    }

    return new Proxy(dict, {
        get(target, prop) {
            if (typeof prop === 'string') {
                const norm = normalizeSearchTerm(prop);
                if (norm in target) {
                    return target[norm];
                }
            }
            return Reflect.get(target, prop);
        }
    });
}
