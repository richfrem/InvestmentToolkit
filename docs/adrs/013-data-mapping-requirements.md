# ADR 013: Data Mapping from Source to Destination Schemas

## Status
Accepted

## Context
The application processes data from multiple sources (Questrade API, internal data stores, portfolio master data) and transforms it through various pipelines. Without explicit data mapping requirements, transformations can become inconsistent, error-prone, and difficult to maintain. This ADR establishes requirements for all data transformations to ensure reliability and maintainability.

## Decision
All data transformations between source and destination schemas must follow these requirements:

1. **Explicit Field Mapping**: Every transformation must document source-to-destination field mappings
2. **Type Conversion Rules**: Clear rules for data type conversions and validations
3. **Schema Validation**: Runtime validation of transformed data against destination schemas
4. **Versioning**: Data mapping rules must be versioned and tracked
5. **Documentation**: All mappings must be documented in code comments and/or separate mapping files
6. **Testing**: Automated tests for data transformation pipelines

## Key Data Transformations Covered

### Questrade API → Internal Holdings
- **Source**: Questrade positions/balances API responses
- **Destination**: Internal Holding interface
- **Mapping Rules**:
  - `symbol` → `symbol` (string)
  - `openQuantity` → `quantity` (number, default 0)
  - `currentMarketValue` → `marketValue` (number, default 0)
  - `averageEntryPrice * openQuantity` → `bookValue` (number, default 0)

### Holdings Aggregation → Portfolio Master Data
- **Source**: Aggregated holdings across accounts (Logic managed in Python services)
- **Destination**: `investment_screener/frontend/src/data/portfolio.json`
- **Mapping Rules**:
  - Holdings grouped by symbol with pillar mapping
  - Percentage calculations based on total portfolio value
  - Gap calculations: `currentAllocation - targetAllocation`

### Portfolio Master Data → Analysis Reports
- **Source**: `portfolio_master_data.json`
- **Destination**: Markdown tables, charts, LLM analysis inputs
- **Mapping Rules**:
  - Pillar totals calculated from holdings
  - Allocation gaps highlighted with color coding
  - Target vs actual comparisons

## Detailed Field Mapping Table: Questrade API → Portfolio Master Data

| Source Field (Questrade API) | Destination Field (Portfolio Master Data) | Type | Transformation Rules | Validation |
|------------------------------|-------------------------------------------|------|---------------------|------------|
| `positions[].symbol` | `currentHoldings[].symbol` | string | Direct copy | Required, non-empty |
| `positions[].name` | `currentHoldings[].name` | string | Direct copy, fallback to '' | Optional |
| `positions[].openQuantity` | `currentHoldings[].totalShares` | number | Sum across accounts, default 0 | ≥ 0 |
| `positions[].currentMarketValue` | `currentHoldings[].totalMarketValue` | number | Sum across accounts, default 0 | ≥ 0 |
| `positions[].averageEntryPrice * openQuantity` | `currentHoldings[].totalBookValue` | number | Sum of (avgEntryPrice × quantity) across accounts | ≥ 0 |
| `getPillarForSymbol(symbol)` | `currentHoldings[].pillar` | string | Lookup from symbol_pillar_mappings.json | Must match pillar names |
| `totalMarketValue / current.totalMarketValue` | `currentHoldings[].pctPortfolio` | number | Percentage calculation | 0-100 |
| `positions[].accountNumber` | `currentHoldings[].accounts[]` | string[] | Array of account numbers | Non-empty array |
| `aggregatedHoldings` | `pillarTotals[pillar]` | number | Sum of market values by pillar | ≥ 0 |
| `currentAllocation - targetAllocation` | `symbolAllocations[].gap` | number | Difference calculation | Can be negative |
| `currentMarketValue / totalMarketValue` | `symbolAllocations[].currentAllocation` | number | Percentage of total portfolio | 0-100 |
| `targetAllocation / 100` | `symbolAllocations[].targetAllocation` | number | Convert percentage to decimal | 0-1 |
| `openQuantity` | `symbolAllocations[].openQuantity` | number | Direct copy from positions | ≥ 0 |
| `totalCost` | `symbolAllocations[].totalCost` | number | Book value from positions | ≥ 0 |
| `averageEntryPrice` | `symbolAllocations[].averageEntryPrice` | number | Direct copy | ≥ 0 |
| `currentPrice` | `symbolAllocations[].currentPrice` | number | marketValue / quantity | ≥ 0 |
| `currentMarketValue` | `symbolAllocations[].currentMarketValue` | number | Direct copy | ≥ 0 |
| `totalMarketValue - totalBookValue` | `symbolAllocations[].openPnl` | number | Unrealized P&L calculation | Can be negative |
| `new Date().toISOString()` | `lastUpdated` | string | Current timestamp | Valid ISO date |
| `aggregatedHoldings` | `totalMarketValue` | number | Sum of all holdings market values | ≥ 0 |

## Pros
- Prevents data corruption and transformation errors
- Enables reliable debugging and maintenance
- Supports automated testing and validation
- Clear documentation for future developers

## Cons
- Requires upfront documentation effort
- Slight development overhead for complex transformations

## Alternatives Considered
- Implicit mappings (error-prone, hard to maintain)
- No validation (risky for data integrity)
- External mapping tools (overkill for current complexity)

## Consequences
- All data transformations now require explicit mapping documentation
- New transformations must include validation and testing
- Data integrity is maintained across the entire pipeline
- Easier debugging and maintenance of data flows

## Implementation
- Document mappings in code comments for simple transformations
- Create separate mapping files for complex transformations
- Include validation functions for all data transformations
- Add unit tests for transformation pipelines

---

**Related Requirements:**
- UR32: Data mapping from source to destination schemas must be explicit, documented, and validated