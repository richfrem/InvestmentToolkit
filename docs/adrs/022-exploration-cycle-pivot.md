# ADR 022: Pivot to Exploration Cycle Architecture

## Status
Accepted

## Context
Previously, the project used the **Spec Kitty** framework to systematize AI agent workflows. Spec Kitty relied on a specific CLI and template-driven missions to guide development. However, as the project evolved, a more flexible and modular approach was needed to handle the complex "discovery to prototype" lifecycle. 

The project has now pivoted to using the **Exploration Cycle Plugin** (a specialized modification of the orba/superpowers plugin).

## Decision
We will replace the Spec Kitty framework with the **Exploration Cycle** architecture. This transition involves:

1.  **Decommissioning Spec Kitty**: Removal of `.kittify/` directories and Spec Kitty-specific task files (e.g., `task.md`).
2.  **Adopting Phase-Based Exploration**: Implementing a 4-phase lifecycle managed by the `exploration-workflow` skill:
    *   **Phase 1: Problem Framing** (Discovery Planning)
    *   **Phase 2: Visual Blueprinting** (Layout Confirmation)
    *   **Phase 3: Prototyping** (Subagent-Driven Construction)
    *   **Phase 4: Handoff & Specs** (Final Synthesis)
3.  **Modular Agent Integration**: Utilizing specialized agents for different stages of the lifecycle:
    *   `intake-agent`: Front-door interviewer for pre-filling session briefs.
    *   `exploration-cycle-orchestrator`: Director for discovery and requirements capture.
    *   `requirements-doc-agent`: Low-cost CLI-dispatched agent for focused documentation passes.
4.  **Stateful Session Management**: All exploration state is now managed via a local `exploration/exploration-dashboard.md` file, providing a clear human-readable audit trail.

## Consequences
*   **Decoupling**: The project is no longer dependent on the Spec Kitty CLI or its internal mission structure.
*   **Traceability**: Every feature or architectural pivot now begins with an `exploration/session-brief.md` and follows a documented path.
*   **Lower Token Costs**: By using focused, low-cost CLI sub-agents for documentation passes, we reduce the token load on the primary model.
*   **Human-in-the-Loop**: The 4-phase gate system ensures the SME (Subject Matter Expert) provides explicit approval at each critical juncture (Planning, Design, Prototype).
*   **Re-entry Support**: The architecture natively supports "re-entry spikes," allowing developers to jump back into discovery if implementation uncovers unresolved ambiguity.
