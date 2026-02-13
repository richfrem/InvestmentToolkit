# APP-TEMPLATE: [Application Name]

## Application Profile
*   **Code:** [Acronym]
*   **Name:** [Full Name]
*   **Primary Users:** [User Groups]
*   **Entry Point:** [Main Menu Form link]

## Purpose
[High-level overview]



## Key Modules & Functionality
| Form ID | Name | Purpose |
| :--- | :--- | :--- |
| **FORM01** | Name | Description |

## Application Menus
*   **Source:** `Appl4 Menu Item Rules.csv`
*   **Manual Override:** `[Acronym]-Application-Override.md`

| Menu Item | Screen Label | Roles with Access |
| :--- | :--- | :--- |
| **MENU.ITEM** | Label | [Roles] |

## Validated Dependencies
Derived from `form_relationships.csv`.

| Target Form | Description | Status / Logic |
| :--- | :--- | :--- |
| **[FORM_ID]** | Function | **Active**: Role dependent |
## User Roles
### Active Roles
Roles verified in the current security inventory.
*   **[ROLE_NAME]**

### Legacy / Deprecated Roles
Roles referenced in menu rules but not present in the active security inventory.
*   **[OLD_ROLE]**

## Integration Points
*   **[App/System Name]:** [Data exchange description]

## Technical Context
*   **Main Menu:** `[FORM_ID]`
*   **Libraries:** `[LIB_NAME]`
