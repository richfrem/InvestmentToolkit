# {OBJECT_NAME} - Database Object Overview

## Object Information
| Property | Value |
|---|---|
| **Object Name** | `{OBJECT_NAME}` |
| **Type** | Table / View / Function / Procedure / Package / Sequence / Type |
| **Schema** | {SCHEMA_NAME} |
| **Source File** | `legacy-system/oracle-database/{Type}/{filename}.sql` |
| **Last Analyzed** | {DATE} |

## Purpose
{Brief description of the object's purpose in the system.}

## Structure (for Tables/Views)
| Column | Type | Nullable | Description |
|---|---|---|---|
| {COLUMN_NAME} | {DATA_TYPE} | Yes/No | {DESCRIPTION} |

## Parameters (for Functions/Procedures)
| Parameter | Direction | Type | Description |
|---|---|---|---|
| {PARAM_NAME} | IN/OUT/INOUT | {TYPE} | {DESCRIPTION} |

## Business Logic (for Functions/Procedures/Packages)
{Summary of the key logic implemented.}

## Constraints (for Tables)
| Constraint | Type | Definition |
|---|---|---|
| {CONSTRAINT_NAME} | PK/FK/CHECK/UNIQUE | {DEFINITION} |

## Indexes (for Tables)
| Index | Columns | Unique |
|---|---|---|
| {INDEX_NAME} | {COLUMNS} | Yes/No |

## Dependencies
### Used By
| Object | Type | Usage |
|---|---|---|
| {OBJECT_NAME} | Form/Report/Package | {USAGE} |

### Uses
| Object | Type |
|---|---|
| {OBJECT_NAME} | Table/View/Package |

## Business Rules Enforced
{List any business rules enforced by this object (constraints, triggers, validation).}

## Notes
{Any additional observations or migration considerations.}
