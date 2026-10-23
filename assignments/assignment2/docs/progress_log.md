# Progress Log — CIS I Assignment 2

Operation log. Read on demand only. Format and workflow: see AGENTS.md §5.
- `## Pending`: one line per permitted file change, appended at the end of that section.
- `## Commits`: one block per work commit (commits whose message starts with `log:` are skipped), oldest first.

---

## Phase 0 planning record (2026-10-20 ~ 10-23 | Claude desktop app, Opus 5.5)
Agreed details for later phases. Copy the relevant part into AGENTS.md §6 when a phase starts.

### Phase 2 — Variable table (→ report/sections/02_variables.tex)
- Generated once, after all 6 reading segments are confirmed.
- Columns: Symbol | Meaning | Value / range | Unit | Type | Source (page)
- Type ∈ {given, design, estimated, nuisance, target}
- Groups: frames; kinematic parameters; robot errors; tracker errors; timing & motion; accuracy targets
- Faithful to the handout: write "not specified" where no value is given; keep typos as written and footnote them.
- LaTeX: booktabs + longtable, following the A1 table style (course_reference Part 2.4).

### Phase 3 — Theory (→ report/sections/03_mathematical_approach.tex)
1. Linearized error model: Jacobian of ΔF_ee with respect to Δθ_sys, φ_k, ΔF_we.
2. Identifiability: coupling and gauge freedom with F*_rob and F_tracker (e.g., base rotation vs. φ2, φ3); Jacobian rank.
3. Sample spacing from the interpolation error bound (ω h/2).
4. Measurement error propagation: marker noise and tracker distortion → pose → parameters.
5. Total error budget.
6. Improved inverse kinematics and convergence of the iterative correction.

### Phase 4 — Design items (after theory)
1. Tracker pose F_tracker
2. Robot pose F_rob
3. mBee geometry (‖a*_k‖ ≤ 75 mm, defined once)
4. Optional extra reference marker bodies
5. Data-collection plan: positions, spacing, samples per pose, motion order
6. Data processing and parameterization (interpolation of Δθ_sys, nuisance parameters)
7. ImprovedFwdKins / ImprovedInvKins
8. Test plan and unit tests
9. Error-budget allocation

### Phase 0 work summary
- Condensed the lecture notes (frames, least squares, interpolation, rigid 3D-3D, localizers, calibration) and the user's interpolation guide into docs/course_reference.md Part 1.
- Condensed the A1 report format (structure, preamble, notation, table styles) into Part 2; full source in docs/a1_report.tex.
- Condensed the A2 handout (with page references), handout inconsistencies, working understanding and error-budget notes into Part 3.
- Set up AGENTS.md (rules, notation, file index, log/git workflow, progress), CLAUDE.md (`@AGENTS.md`), report/main.tex, .gitignore (.DS_Store).

---

## Pending
- 10-23 17:10 | Claude desktop (Opus 5.5) | docs/course_reference.md | created from Project Context reference (English, 3 parts)
- 10-23 17:10 | Claude desktop (Opus 5.5) | docs/a1_report.tex | added A1 report LaTeX source (verbatim)
- 10-23 17:10 | Claude desktop (Opus 5.5) | AGENTS.md | rewrote rules, file index, log/git workflow, progress plan
- 10-23 17:10 | Claude desktop (Opus 5.5) | docs/progress_log.md | created log with Phase 0 planning record
- 10-23 17:10 | Claude desktop (Opus 5.5) | report/main.tex | added A2 main file (A1 preamble, A2 title page, section inputs)
- 10-23 17:10 | Claude desktop (Opus 5.5) | ../../.gitignore | added .DS_Store

---

## Commits
(none logged yet)
