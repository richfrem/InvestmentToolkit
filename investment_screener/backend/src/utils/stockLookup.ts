/**
 * stockLookup.ts
 * =====================================
 * Utility functions for compiling and normalizing a fuzzy stock ticker lookup dictionary.
 */

export function normalizeSearchTerm(term: string): string {
    return term
        .toUpperCase()
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, '') // remove punctuation
        .replace(/\s+/g, ' ')                      // normalize whitespace
        .trim();
}

export function stripSuffixesStages(normalizedName: string): string[] {
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

export function stripSuffixes(normalizedName: string): string {
    const stages = stripSuffixesStages(normalizedName);
    return stages[stages.length - 1];
}

export function buildLookupDictionary(holdings: any[]): Record<string, string> {
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
