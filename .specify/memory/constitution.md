<!--
    SYNC IMPACT REPORT

    - Version: 1.0.0 -> 1.1.0
    - Change: MINOR (New section added, principle refined)
    - Principles Modified:
        - "4. Colab-First Deployment" (Description refined)
    - Sections Added:
        - "Current Project Status"
    - Sections Removed:
        - None
    - Templates requiring updates (✅ updated / ⚠ pending):
        - ✅ .specify/templates/plan-template.md (Checked implicitly, no specific rules to adjust in template)
        - ✅ .specify/templates/spec-template.md (Checked implicitly, no specific rules to adjust in template)
        - ✅ .specify/templates/tasks-template.md (Checked implicitly, no specific rules to adjust in template)
        - ✅ .specify/templates/commands/constitution.md (This command file itself, updated implicitly as part of agent's execution)
        - ⚠ README.md (Manual follow-up recommended for consistency with new "Current Project Status" and Colab-first emphasis)
        - ⚠ docs/quickstart.md (If exists, manual follow-up recommended to update deployment instructions)
    - Follow-up TODOs:
        - Ensure documentation (especially README and quickstart guides) explicitly reflect the Colab-first deployment and current project status.
-->

# Constitution of openshorts

This document outlines the core principles that guide the development and decision-making for the openshorts project.

## Governance

-   **Constitution Version**: 1.1.0
-   **Ratification Date**: 2026-02-11
-   **Last Amended Date**: 2026-02-12

### Amendment Process

Amendments to this constitution require a formal proposal and review process. Changes are classified by impact:
-   **MAJOR**: Fundamental changes, removal of principles, or backward-incompatible alterations.
-   **MINOR**: Addition of new principles or significant expansions.
-   **PATCH**: Minor clarifications, typo fixes, or rephrasing.

All changes must be documented in the sync impact report at the top of this file.

---

## **Preamble**

This constitution establishes a set of fundamental principles to which all code, features, and architectural decisions within the `openshorts` project MUST adhere. Its purpose is to ensure the project achieves its goal of becoming a superior, professional-grade alternative to existing video clipping solutions, with a focus on quality, performance, and sustainability.

## Current Project Status

The `openshorts` project is currently in a half-complete state, with core functionalities established. The existing codebase primarily leverages Python for backend logic, including video processing (`editor.py`), AI prompting (`prompts.py`), and subtitle generation (`subtitles.py`). A web-based dashboard (`dashboard/`) provides the user interface. Data persistence and logging is not yet implemented but is planned to be managed through Google Sheets, with Google Drive for video asset storage. Local execution is not the primary operational model; instead, the project is designed for execution and testing within Google Colab environments, facilitated by `colab.py`.

---

## **Principles**

### 1. Professional-Grade User Experience

-   **Description**: The application MUST provide a clean, intuitive, and consistent user interface. The user experience should be seamless and demonstrably superior to existing short-form video clipping solutions. Every feature will be designed with the user's workflow in mind to maximize ease of use and efficiency.
-   **Rationale**: A high-quality user experience is critical for user adoption and retention. By prioritizing a professional and polished interface, we aim to establish the project as a leader in its category.

### 2. High-Performance Processing

-   **Description**: All video processing and analysis tasks MUST be optimized for speed and resource efficiency. The system should process videos in a timely manner, providing rapid results to the user without compromising on the quality of the output.
-   **Rationale**: Long waiting times for video processing are a major point of friction for users. Optimizing for performance is key to a positive user experience and the scalability of the application.

### 3. Maintainable and Scalable Codebase

-   **Description**: The codebase MUST be well-structured, following modern design patterns and best practices. All code should be clear, commented where necessary, and accompanied by relevant documentation and tests. The architecture should be modular to allow for future scalability and the addition of new features without major refactoring.
-   **Rationale**: A sustainable project requires a codebase that is easy to understand, maintain, and extend. This discipline allows for long-term development, easier onboarding of new contributors, and reduces the likelihood of bugs.

### 4. Colab-First Deployment

-   **Description**: The project MUST be fully functional and easily runnable within a Google Colab environment, specifically leveraging `colab.py` for streamlined execution and testing. This includes efficient dependency management, straightforward configuration, and comprehensive documentation for a one-click deployment experience. Any reliance on local machine setups is to be avoided.
-   **Rationale**: To ensure broad accessibility for users and contributors, the primary target environment is Google Colab. This removes barriers to entry, simplifies setup, and ensures a consistent execution environment for everyone.

### 5. Comprehensive Testing and Quality Assurance

-   **Description**: Every new feature or change MUST be accompanied by a suite of tests, including unit, integration, and end-to-end tests where appropriate. The project will maintain a high level of test coverage to ensure stability and prevent regressions.
-   **Rationale**: A rigorous testing culture is essential for building a reliable and professional application. It ensures that the software works as expected, gives confidence when refactoring, and is crucial for the long-term health of the project.