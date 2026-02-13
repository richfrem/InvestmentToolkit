# [ID] - [Form Title]

> [!NOTE]
> **Human Verification**: This document includes manually verified overrides.
> See [OverrideFile.md] (Reference Missing: file.md).


## Overview
[High-level summary of the form's purpose, primary users, and critical nature. E.g., "Central Court Inquiry screen used by courts, crown, and RCC staff..."]

## Applications with Access
*   **[App Code]**: [App Name] (e.g., JCSM0000 - JUSTIN COURTS SYSTEM Main Page)

## Functional Description
[Detailed description of functionality. Match legacy PDF content if available.]

### Key Blocks
*   **[BLOCK_NAME]**: [Description]

## Technical Implementation
> [!TIP]
> Use `py scripts/documentation/find_source_links.py <ID>` to generate these links automatically.

*   **Form Module**: [FORM_NAME].fmb [[MD] (Reference Missing: path)] [[XML] (Reference Missing: path)]
*   **Menu Module**: [MENU_NAME] (e.g., `juslib`)
*   **Libraries Attached**:
    *   [LIB_NAME] [[PLL] (Reference Missing: path)] [[XML] (Reference Missing: path)]

## Access & Security
> [!IMPORTANT]
> Access can be enforced at multiple layers (Application, Agency, Role, or Form-Specific Logic).

### User Roles

#### Active Roles
Roles verified in the current security inventory.

| Application | Allowed Roles |
| :--- | :--- |
| **[App Code]** | **[ROLE_NAME] (Reference Missing: role_name.md)** |

#### Legacy / Deprecated Roles
Roles referenced in legacy documentation but not present in the active security inventory.

| Application | Allowed Roles |
| :--- | :--- |
| **[App Code]** | **LEGACY_ROLE** |

> [!IMPORTANT]
> **Role Validator Algorithm**: You MUST traverse dependencies 1-level deep from the Main Menu to find all roles.
> See [Policy Section 1.5](../../.agent/rules/legacy-system-analysis/form_documentation_policy.md#15-role-validator-algorithm-mandatory).
| **JCS** | `JCS_COURTS_CLERK` |

### Security & Restrictions
#### Application-Wide Rules
*   **Agency Boundary**: [e.g., "Users restricted to their own agency unless role X"]
*   **Role-Based Visibility**: [e.g., "Crown cannot see Y tab"]

#### Form-Specific Rules
*   **Preconditions**: [e.g., "RCC must be approved"]
*   **Specific Access Levels** (If Applicable):
    *   **Level 1**: General Access
    *   **Level 2**: Limited/Youth
    *   **Level 3**: Restricted/Ban

### Exhaustive Role-Based Access Table
> [!NOTE]
> This table MUST be exhaustive. Include every menu item, button, or UI element with restricted access.
> Generated from `aPPL4 Menu Item Rules.csv` or legacy analysis.

| ITEM_NM | ITEM_TYPE | Roles with Access | Roles with Display Only |
| :--- | :--- | :--- | :--- |
| `MENU_ITEM_NAME` | MIP | `ROLE_1`, `ROLE_2` | `ROLE_3` |

## Application Menus (For Application Overviews Only)
> [!IMPORTANT]
> This section is REQUIRED for **Application Overviews** and **Main Menu Forms** (e.g., `JASM0000`).
> It summarizes the top-level menu structure defined in `Appl4 Menu Item Rules.csv`.

**Source:** [`Appl4 Menu Item Rules.csv`](../../legacy-system/reference-data/collections/appl4/Appl4 Menu Item Rules.csv)

| Menu Item | Screen Label (Description) | Roles with Access |
| :--- | :--- | :--- |
| **ADMIN_MENU.JASE0001** | Update RCC Information | [`JAS_ADMIN`](../../legacy-system/justin-roles/JAS_ADMIN.md), [`JAS_CSB_BI_USER`](../../legacy-system/justin-roles/JAS_CSB_BI_USER.md) |
| **ADMIN_MENU.JUSE0100** | Reports | [`JAS_USER`] (Reference Missing: jas_user.md) |


## Business Rules (Discovered Logic)
> [!NOTE]
> Extracted from `pre-insert`, `when-validate-item`, and PL/SQL packages.

### UI Logic & Visibility
*   **[Element_Name]**: [Condition] -> [Effect] (e.g., "Crown cannot see Y tab")

### Data Validation Rules
*   **[BR-XXXX] (Title):** [Trigger] - [Description]
    *   *Confidence:* HIGH/MEDIUM/LOW
    *   *Source:* [File]:[Line]

## Navigation

### Parent (Caller) Forms
> [!NOTE]
> Forms that can invoke this form, with their access control mechanisms.

| Parent Form | Invocation Method | Roles Able to Invoke | Access Control Mechanism |
# [Form ID] - [Form Title]

## Form Information
| Property | Value |
|---|---|
| **Form ID** | [Form ID] |
| **Title** | [Form Title] |
| **Application** | [APP] ([App Name]) |
| **Type** | [Form Type] (e.g. Maintenance, Inquiry, Modal) |
| **Analysis Status** | Analyzed |

> **Source Documents:**
> - [Link to Functional Spec if available]

**Object ID:** [[Form ID]] [[overview]] (Reference Missing: [Form ID]-Overview.md) [[xml-md]] (Reference Missing: [Form ID lower]-FormModule.md) [[xml]] (Reference Missing: [Form ID lower]_fmb.xml)

## Purpose
[Brief summary of what the form does, who uses it, and its business value.]

## Validated Dependencies

### Upstream Dependencies
> **Who calls this form?** (Parent Callers)

| Calling Object | Type | Method |
| :--- | :--- | :--- |
| **[PARENT_ID] (Reference Missing: PARENT_ID-Overview.md)** | Form/Menu | `CALL_FORM` / Menu Item |

### Downstream Dependencies
> **Who does this form call?** (Child Calls)

| Called Object | Type | Method |
| :--- | :--- | :--- |
| **[CHILD_ID] (Reference Missing: CHILD_ID-Overview.md)** | Form | `OPEN_FORM` |

### Attached Libraries (PLL)
| Library | Purpose | Status |
| :--- | :--- | :--- |
| **[LIBNAME] (Reference Missing: LIBNAME-Library-Overview.md)** | Shared Utils | **Active** |

### Database Objects
| Object | Type | Usage |
| :--- | :--- | :--- |
| **[PKG_NAME] (Reference Missing: PKG_NAME.md)** | Package | Core Business Logic |

## Navigation
- **Menu Item:** `[Menu Path]`
- **Entry Point:** `[Call_Form Procedure Name]`
- **Parameter List:** `[Param List Name]`

## Application(s) with Access
> **Discovery Command:** `cli.py applications --target [FormID]`

| Application | Main Menu | Notes |
|-------------|-----------|-------|
| **[JAS](../../legacy-system/applications/JAS-Application-Overview.md)** | [JASM0000](../../legacy-system/oracle-forms-overviews/forms/JASM0000-Overview.md) | [Access Description] |

## Security
> [!IMPORTANT]
> Access is enforced at multiple layers: APPL4 config (UI/menu), triggers (workflow), and backend PL/SQL.

### User Roles
#### Active Roles
Roles verified in the current security inventory.

| Application | Allowed Roles |
| :--- | :--- |
| **[APP]** | **[ROLE_NAME]** |

#### Legacy / Deprecated Roles
Roles referenced in legacy documentation or code but not present in the active security inventory.

| Application | Restricted Roles |
| :--- | :--- |
| **[APP]** | `UNKNOWN_ROLE` |

> [!TIP]
> **Analysis Note (Application vs Role Variance):**
> Compare `Application(s) with Access` against `Active Roles`. If an app is reachable but has no explicit roles:
> - **Shared Role:** Access via cross-app role (e.g., `JAS_CEIS_USER` grants JAS users access via JCS).
> - **Legacy/Hidden:** App is deprecated or form is hidden from that app's users.
> - **Menu-Only:** Roles are defined at a parent menu level, not directly on this form.
## Business Rules

*   **[BR-XXXX] ([Title]):** [Description of the rule].
    *   *Technical Implementation:* [Trigger/Procedure] (`[Code Snippet/Variable]`)
*   **[BR-XXXX] ([Title]):** [Description of the rule].
    *   *Technical Implementation:* [Trigger/Procedure] (`[Code Snippet/Variable]`)

## Functionality
1.  **[Feature 1]:** [Description]
2.  **[Feature 2]:** [Description]

### UI Items & Role-Based Visibility
| Element | Condition | Effect |
|---------|-----------|--------|
| [Item Name] | [Logic] | [Effect] |

## APPL4 UI Access Table (Key Items)
| Item Name | Type | Roles with Access | Roles with Display Only |
|---|---|---|---|
| **[MENU_ITEM]** | MIP | [Roles] | [Roles] |
| **[BUTTON]** | IP | [Roles] | - |

## Fine-Grained Access Control Rules
| Rule/Condition | Code Location | Description |
|---|---|---|
| **[BR-XXXX]** | [Source] | [Description] |

## Technical Implementation
- **Source Code:** [[xml]] (Reference Missing: [Form ID lower]_fmb.xml) [[xml-md]] (Reference Missing: [Form ID lower]-FormModule.md)
- **Attached Libraries:** [List]

## Source Artifact Traceability (Optional)
> Include links to source analysis artifacts when available.

*   [Form XML/Markdown] (Reference Missing: path)
*   [UI Access Table] (Reference Missing: path)
*   [Parent Callers Summary] (Reference Missing: path)

## Screenshots
![Form Screenshot] (Reference Missing: [ID].png)
