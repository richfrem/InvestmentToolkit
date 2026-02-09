# UR23: Portfolio Alignment Table Generation Script

## Overview
Create a script in `scripts/` that reads exported portfolio data, aggregates holdings across accounts, compares actual allocations to thesis targets, highlights gaps, and outputs analysis for LLM review.

## Requirements

### Script Location and Execution
**Description:** Script located in `scripts/` directory with clear execution instructions.

**Requirements:**
- File: `scripts/generate_portfolio_alignment_table.ts`
- Executable via npm script or direct ts-node execution
- Clear command-line interface
- Error handling and user feedback

**Acceptance Criteria:**
- Script discoverable and executable
- Clear usage instructions
- Proper error handling
- Success/failure feedback

### Data Input Processing
**Description:** Read and process `exportedData.json` from backend.

**Requirements:**
- Read `backend/exportedData.json`
- Validate data structure and completeness
- Handle missing or corrupted data gracefully
- Support multiple account aggregation

**Acceptance Criteria:**
- Robust file reading and parsing
- Data validation before processing
- Error recovery for invalid data
- Multi-account support

### Holdings Aggregation Logic
**Description:** Aggregate holdings across all accounts with proper calculations.

**Aggregation Requirements:**
- Grand total shares per symbol
- Average value calculations
- Percentage of total portfolio value
- Per ticker/pillar breakdowns

**Acceptance Criteria:**
- Accurate mathematical calculations
- Consistent aggregation logic
- Proper handling of multiple accounts
- Financial calculation precision

### Thesis Target Comparison
**Description:** Compare actual allocations against thesis target percentages.

**Comparison Requirements:**
- Load thesis target allocations
- Calculate allocation percentages
- Identify over/under allocations
- Gap analysis per pillar/symbol

**Acceptance Criteria:**
- Accurate percentage calculations
- Clear gap identification
- Thesis target data integration
- Consistent comparison methodology

### Gap and Issue Highlighting
**Description:** Highlight gaps, overweights, underweights, and thesis breakers.

**Highlighting Requirements:**
- Visual indicators for deviations
- Clear categorization of issues
- Priority ranking of problems
- Actionable gap information

**Acceptance Criteria:**
- Clear visual highlighting
- Problem categorization
- Priority assessment
- Actionable insights

### Output Format and Location
**Description:** Generate markdown table output to `TargetPortfolio/portfolio_thesis_alignment_report.md`.

**Output Requirements:**
- Markdown table format
- Comprehensive data presentation
- LLM-readable structure
- Human-readable formatting

**Acceptance Criteria:**
- Proper markdown syntax
- Complete data representation
- LLM compatibility
- Human readability

### LLM Integration
**Description:** Output designed for LLM analysis and recommendation generation.

**Integration Requirements:**
- Structured data format
- Clear analysis prompts
- Recommendation framework
- Update mechanisms for targets/gaps

**Acceptance Criteria:**
- LLM-parseable output
- Analysis-ready data structure
- Recommendation support
- Iterative improvement capability

## Technical Specifications

### Script Structure
```typescript
// Main execution flow
async function generatePortfolioAlignmentTable() {
  // 1. Read exported data
  // 2. Validate and aggregate holdings
  // 3. Load thesis targets
  // 4. Calculate allocations and gaps
  // 5. Generate markdown output
  // 6. Write to target file
}
```

### Data Processing Pipeline
```
Raw Data → Validation → Aggregation → Comparison → Analysis → Output
```

### Output Schema
```markdown
# Portfolio Alignment Report

## Holdings Summary
| Symbol | Actual % | Target % | Gap % | Pillar |
|--------|----------|----------|-------|--------|
| ...    | ...      | ...      | ...   | ...    |

## Pillar Analysis
[Gap analysis by investment pillar]

## Recommendations
[LLM-generated recommendations]
```

## Dependencies
- File system access for reading/writing
- JSON parsing capabilities
- Markdown generation
- Thesis data access
- Error handling utilities

## Testing
- Data file availability testing
- Calculation accuracy verification
- Output format validation
- Error condition handling
- LLM compatibility testing