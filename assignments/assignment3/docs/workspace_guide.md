# Assignment 3 workspace guide

## Start here
This is the team's working branch, `assignment3`. It was created from course main `d91ea42` and currently adds documentation and an empty report framework. No A3 solution algorithms or experiments have been implemented. The report skeleton compiles; this does not mean that the assignment notebook or student stubs are complete.

Read this guide for orientation, the original [README](../README.md) for installation and execution, and [AGENTS.md](../AGENTS.md) for assistant instructions. Task requirements come from the [A3 handout](2026_assignment_3.pdf), not from historical reports or the A1 rubric.

## Folder layout and ownership
```text
CIS_I_Course/
├── data_types/                   Course geometry types; shared dependency
└── assignments/
    ├── assignment1/              Original course files; A3 imports tracker support
    ├── assignment2/              Original course-main folder; no local A2 report/build
    └── assignment3/
        ├── README.md             Original course setup, interfaces and task guide
        ├── requirements.txt      Original course dependencies
        ├── sessions.jsonl        Course-provided file; not a team-generated results log
        ├── data/                 Course femur mesh and patch-box data
        ├── src/
        │   ├── mesh.py           Course mesh loading and patch geometry
        │   ├── session.py        Course Session/RemoteSession interface
        │   └── student/
        │       ├── closest_point.py  Student algorithm stub
        │       ├── icp.py            Student algorithm stub
        │       ├── uncertainty.py    Student algorithm stub
        │       ├── workflow.py       Student workflow stub
        │       └── report.py         Provided RegistrationReport format
        ├── tests/                Course tests, including TODO cases
        ├── notebooks/            Course assignment3_template.ipynb
        ├── AGENTS.md             Added: common assistant rules and phase progress
        ├── CLAUDE.md             Added: loads AGENTS.md
        ├── .gitignore            Added: ignores report/build; includes docs PDFs
        ├── docs/                 Added: task/reference/team working documents
        └── report/               Added: team LaTeX framework
```
The simulation runs on the course server. Keep the full course repository because A3 depends on shared types and A1 tracker support. Installation and server access instructions remain in the original README; this guide does not duplicate credentials or change the server interface.

## What differs from course main
At the setup baseline, all existing course files are unchanged: README, requirements, data, source, tests and notebook. Only `assignment3/.gitignore`, `AGENTS.md`, `CLAUDE.md`, `docs/` and `report/` were added. A1/A2 folders and the root `.gitignore` match course main.

Use these commands from the repository root to inspect the current difference; later implementation commits may add to it:
```bash
git diff --name-status main...HEAD
git status --short
```
The first command shows committed branch changes; the second includes current uncommitted changes. A comparison against the latest course version requires deliberately updating/fetching the relevant reference first.

Complete A2 work remains on the `assignment2` and `assignment2_code` branches. The A3 checkout retains only its distilled reference. Do not merge the whole A2 branch into A3 or copy its result tables into the new report.

## Added documents
| File | Purpose | Read when |
|---|---|---|
| `docs/2026_assignment_3.pdf` | Authoritative assignment handout | Reading requirements and checking sources |
| `docs/course_reference.md` | Part 1: lectures; Part 2: A1 report format; Part 3: A2 distilled lessons; Part 4: A3 requirements, discrepancies and living notation | Looking up the relevant topic without rereading whole reports |
| `docs/a1_report.tex` | Full historical A1 format reference | A specific layout example is needed; not an A3 solution |
| `docs/rubric1.jpg` ... `rubric4.jpg` | Photographed A1 rubric, partly cropped | Checking the origin of transferable feedback |
| `docs/report_guidelines.md` | A3 report guidance with source boundaries and A1 lessons | Planning and reviewing report sections |
| `docs/progress_log.md` | Pending changes and work-commit summaries | Resuming work or preparing a commit |
| `docs/ai_assistance.md` | Working material for AI/tool disclosure and prompt descriptions | Recording substantive assistance and preparing final attribution |
| `docs/workspace_guide.md` | Team onboarding and directory overview | Starting work in this branch |

There is no `a2_report.tex` copy: A2 is distilled in reference Part 3; complete sources can be read from its preserved branch when needed. Historical A1/A2 values and notation are not A3 requirements.

## Report framework
`report/main.tex` holds the preamble, cover, contents, chapter inclusion and bibliography. Each file in `report/sections/` currently contains only its title and `subfiles` wrapper:

| File | Intended content |
|---|---|
| `01_introduction.tex` | Problem, goals, specifications and scenario context |
| `02_variables.tex` | Notation and frame conventions |
| `03_mathematical_approach.tex` | Needed derivations, assumptions and error analysis |
| `04_algorithmic_approach.tex` | Implemented algorithm steps, inputs/outputs and workflow |
| `05_program_structure.tex` | Modules, major functions and control/data relationships |
| `06_validation.tex` | Component tests, end-to-end checks and experiment methods |
| `07_results.tex` | Measured results, requirement comparisons and limitations |
| `08_ai_assistance.tex` | Actual AI/tool use, prompt descriptions and sources |
| `09_contributions.tex` | Team responsibilities and contributions |

Use `report/figures/` for report assets and ignored `report/build/` for compiled previews. The cover reuses team details as a starting point: verify names, the required JHED IDs and contact details, and obtain fresh signatures before submission. No old signature was copied.

## How the assistant works with the team
1. **Understand the request and inspect the workspace.** Confirm branch and local changes, synchronize safely, and read only relevant instructions/material. Explain meaningful findings and assumptions. Explicitly requested edits can proceed without repeated confirmation for routine steps.
2. **Read A3 before solving it.** Resolve the current question from the handout, then inspect the matching A3 interface/code when needed. Label PDF requirements, starter behavior and unresolved discrepancies separately. Consult A1/A2 only for relevant background.
3. **Develop notation and theory first.** Start from known quantities and the current goal. Define symbols where first needed; derive the implemented formulas and residuals without skipped steps. Keep inputs, unknowns, assumptions and outputs explicit. Use formulas/matrices rather than long prose when clearer.
4. **Design and implement after the theory.** Justify geometry and sampling choices for A3. Implement the student modules against the existing Session and grading signatures. Keep equations, pseudocode, function names and diagrams aligned with the actual code.
5. **Verify before claiming results.** Use independent expected answers, boundary/degenerate/noisy cases and complete runs. Keep truth-based practice APIs out of estimation. Save seeds, settings and outputs; distinguish residuals from TRE and simulated time from wall time.
6. **Maintain the report as work progresses.** Add only relevant material, cite equation sources and distinguish explicit requirements from presentation advice. Compile changed LaTeX and check the rendered output. Record substantive source changes and stage conclusions in the relevant working documents.
7. **Commit/push when requested.** Review the diff and include only intended A3 files. Consolidate the progress log into the work commit, push, then make the separate `log: fill hash for ...` commit and push to replace its TBD hash. State what was published and whether the worktree is clean.

For teammates: state the desired task and files when starting work, avoid changing the same section simultaneously, pull before editing, and preserve uncommitted work. No assistant-to-teammate message is sent unless the user explicitly requests it.

## Current next step and known discrepancies
Setup is complete; the next phase is line-by-line handout reading and clarification before notation/theory. The report contains no A3 results.

The PDF and starter README currently disagree about the TRE target and tracker noise; uncertainty is optional in the PDF but requested by the starter interface. Registration-direction and submission-folder wording also need care. Consult reference Part 4.4; do not silently merge those statements into one requirement or infer hidden server settings from the client.
