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

---

## Commits

### 91ab914 | 2026-10-23 21:20 | "Phase 0: set up docs, rules, log, report skeleton" | pushed
- Agent: Claude desktop (Opus 5.5)
- Changes:
  - docs/course_reference.md: created from Project Context reference (English, 3 parts)
  - docs/a1_report.tex: added A1 report LaTeX source (verbatim)
  - AGENTS.md: rewrote rules, file index, log/git workflow, progress plan
  - docs/progress_log.md: created log with Phase 0 planning record
  - report/main.tex: added A2 main file (A1 preamble, A2 title page, section inputs)
  - Note: a Pending entry also recorded `../../.gitignore` (added .DS_Store); that file is outside `assignment2/` and is not part of this commit.
  - Note: this block was added afterwards in a `log:` commit, since the Pending entries were not merged before the commit.
- Files: AGENTS.md, docs/a1_report.tex, docs/course_reference.md, docs/progress_log.md, report/main.tex

### dcf54bf | 2026-10-23 17:42 | "Rules: per-commit list in AGENTS.md section 6; sync hash on fill" | pushed
- Agent: Claude desktop (Opus 5.5)
- Changes:
  - AGENTS.md: section 5 step 1 and the `log: fill hash` rule now also replace the matching `TBD` in section 6 "Current phase commits" with the hash
  - AGENTS.md: section 5 step 3 now appends `- TBD | MM-DD | <commit message>` to "Current phase commits"; a completed phase is compressed to one line in Completed phases listing only hashes (details in this log)
  - AGENTS.md: section 6 split into Plan (tasks only; Phase 1 output requirements moved above the Seg list), a new "Current phase commits" subsection, and Completed phases; Phase 0 line changed from `commit: see progress_log (first block)` to `commits: 91ab914`
  - docs/progress_log.md: added this block
- Files: AGENTS.md, docs/progress_log.md

### cd9aad0 | 2026-10-23 17:57 | "Rules: typo handling via chat confirmation and Part 3.2" | pushed
- Agent: Claude desktop (Opus 5.5)
- Changes:
  - AGENTS.md: section 2: suspected typos are raised in chat first, then recorded in course_reference.md Part 3.2 as one line (original -> corrected) after user confirmation
  - AGENTS.md: section 6: filled dcf54bf, added TBD line for this commit
  - docs/progress_log.md: filled dcf54bf (pushed), added this block
- Files: AGENTS.md, docs/progress_log.md

### fb2aed1 | 2026-10-23 18:34 | "Rules: Phase 1 output format (translation + code variable names)" | pushed
- Agent: Claude Code (Opus 5.5); Claude desktop (Opus 5.5) for log/commit
- Changes:
  - AGENTS.md: section 6 Phase 1 output format: (a) translation of the original text (b) variables of the segment with the matching code names from `src/`; the "issues" item removed (suspected typos still follow section 2)
  - AGENTS.md: section 6 Phase 1: the LaTeX variable table is written to `report/sections/02_variables.tex` only on user request
  - AGENTS.md: section 6: filled cd9aad0, added TBD line for this commit
  - docs/progress_log.md: filled cd9aad0 (pushed), added this block
- Files: AGENTS.md, docs/progress_log.md

### fddae14 | 2026-10-23 19:45 | "Rules: Unicode formulas in chat, A2-first code reading; reference: tracker API and p2 typos" | pushed
- Agent: Claude Code (Opus 5.5); Claude desktop (Opus 5.5) for log/commit
- Changes:
  - AGENTS.md: section 2 rule: formulas in chat are written as Unicode in code spans, LaTeX only in .tex files
  - AGENTS.md: section 3 rule: read A2 code (`assignment2/src/`) first; follow A1 code only where A2 imports it or the handout/code says so, and cite the source file; A1-only code and constants are not A2 behavior
  - docs/course_reference.md: 3.1 Tracker API: return values of MostRecentObservedFrame / MostRecentObservedMarkers (tracker frame, last sample, no time cost)
  - docs/course_reference.md: 3.2 #10 MostRecentObservedMarkers returns b_m,k, not a_m,k; #11 minor p2 notation typos
  - AGENTS.md: section 6: filled fb2aed1, added TBD line for this commit
  - docs/progress_log.md: filled fb2aed1 (pushed), added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md

### 57a2718 | 2026-10-25 14:57 | "Rules: report holds only content that fits its logic" | pushed
- Agent: Claude desktop (Opus 5.5)
- Changes:
  - AGENTS.md: section 2 rule: report contains only content that fits its logic; chat Q&A and clarifications are not written into it; handout typos only when they affect derivation or implementation
  - AGENTS.md: section 6: filled fddae14, added TBD line for this commit
  - docs/progress_log.md: filled fddae14 (pushed), added this block
- Files: AGENTS.md, docs/progress_log.md

### dc3ef9b | 2026-10-25 16:42 | "Rules: look up local repo before inferring; remote course repo only on request" | pushed
- Agent: Claude Code (Opus 5.5); Claude desktop (Opus 5.5) for log/commit
- Changes:
  - AGENTS.md: section 3 rule: content not given in the handout (usage, workflow, values) is looked up in the local repo without asking: A2 `src/`, `notebooks/`, `tests/`, `README.md` first, then the whole local CIS_I_Course repo (parts not imported by A2 are reference only); answers state whether each item comes from the handout or from code (file name); inference only if nothing is found, labeled as such
  - AGENTS.md: section 3 rule: the remote course repo (github.com/LCSR-CIIS/CIS_I_Course) is checked only on user request, e.g. to compare with the original version of a locally modified file
  - AGENTS.md: section 2: the "only answer by default" rule now names the local-repo lookup as an exception
  - AGENTS.md: section 6: filled 57a2718, added TBD line for this commit
  - docs/progress_log.md: filled 57a2718 (pushed), added this block
- Files: AGENTS.md, docs/progress_log.md

### 7c01a97 | 2026-10-25 18:37 | "Rules: Part 3.5 notation only; reference: handout issues #8-17 (p3-5)" | pushed
- Agent: Claude Code (Opus 5.5); Claude desktop (Opus 5.5) for log/commit
- Changes:
  - AGENTS.md: section 2 rule: Part 3.5 of course_reference.md holds notation only (symbols, meaning, code variables); derivations stay in LaTeX
  - docs/course_reference.md: Part 3.2 revised #8 (σ/δ/ω_sys missing from the CreateRobot signature; σ_sys role from code) and #9 (code values for unspecified items)
  - docs/course_reference.md: Part 3.2 added #12-17 (F*_rob formula, CommandedPose argument, speed-limit product, F_mBee meanings, Figure 1 F_ce/F_c, p3-5 minor typos)
  - AGENTS.md: section 6: filled dc3ef9b, added TBD line for this commit
  - docs/progress_log.md: filled dc3ef9b (pushed), added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md

### 1d78b39 | 2026-10-25 20:37 | "Phase 2: Variables and Notation section; local LaTeX build with tectonic" | pushed
- Agent: Claude Code (Opus 5.5)
- Changes:
  - report/sections/02_variables.tex: Variables and Notation section: conventions (four items), five tables (symbols and code variables, frames by version, exact quantities, error terms and limits, simulator state); bold group headings
  - report/main.tex: load xurl so code names in \path{} break across lines
  - docs/course_reference.md: Part 3.5 notation summary from 02_variables.tex
  - AGENTS.md: section 5/7: check poppler and tectonic before work; agent compiles LaTeX into report/build with tectonic and opens the PDF in the side pane
  - AGENTS.md: section 2/5: user-approved exception for one root .gitignore line; root .gitignore ignores assignments/assignment2/report/build/
  - AGENTS.md: section 6: Phase 1 compressed into Completed phases; Phase 2 is current; filled 7c01a97
  - docs/progress_log.md: filled 7c01a97 (pushed), added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md, report/main.tex, report/sections/02_variables.tex, ../../.gitignore

### 037ed94 | 2026-10-25 22:44 | "Phase 2 done: subfiles build, Part 3.4 clarifications, reference cleanup" | pushed
- Agent: Claude Code (Opus 5.5)
- Changes:
  - report/main.tex, report/sections/*.tex: switched to subfiles; main.tex is the full report (\subfile per chapter; graphicspath also ../figures/); every chapter wraps itself in \documentclass[../main.tex]{subfiles} and compiles alone
  - docs/course_reference.md: new Part 3.4 Clarifications and interim conclusions (Phase 1 distillation, 20 items, basis → conclusion); removed the Phase 0 estimates (old 3.3 working understanding, old 3.4 error-budget notes); renumbered notation to 3.3; 3.1 viewing-volume note cites Tracker.FRUSTUM_*; header lists the Part 3 sections
  - AGENTS.md: section 2: distill non-obvious conclusions into Part 3.4 at phase end after user confirmation; section 5: in report/, log main.tex, sections/ and figures/ only (not build/ or temporary preview chapters); section 7: per-chapter tectonic build via subfiles, fixed relative layout of main.tex/sections/figures, temporary preview chapters deleted after review; section 3 index updated
  - AGENTS.md: section 6: Phase 2 marked complete and compressed into Completed phases; Phase 3 is current; filled 1d78b39
  - docs/progress_log.md: filled 1d78b39 (pushed), added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md, report/main.tex, report/sections/01_introduction.tex … 07_results.tex

### c0c22e1 | 2026-10-25 22:47 | "Reference: resolve tentative handout corrections in Part 3.2" | pushed
- Agent: Claude Code (Opus 5.5)
- Changes:
  - docs/course_reference.md: Part 3.2 #1, #2, #3, #5, #7 made definitive with code/notebook basis (θs → θ2; n1..3 read as n4..6; d*_k ≈ d_k + sk(φ_k) d_k; InvK accuracy uses the reached pose F*_ee(θ); truncated-pyramid volume); added #18 (p6 hint 1(d): Δθ_sys map and φ_k are the unknowns, F*_ee) and #19 (p5–6 minor)
  - docs/course_reference.md: Part 3.1 lines that copy handout errors now point to the matching 3.2 item
  - AGENTS.md: section 6: added TBD line for this commit (Phase 3)
  - docs/progress_log.md: added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md

### 51e03b2 | 2026-10-26 13:51 | "Phase 3: Mathematical Approach draft (error model, gauges, spacing, budget, IK)" | pushed
- Agent: Claude Code (Opus 5.5)
- Changes:
  - report/sections/03_mathematical_approach.tex: full draft: measurement model; first-order error model (tilted revolute joint via conjugation, wrist/tool/base composition, boxed residual, Jacobian column table, decoupling, second-order size); knot parameterization of Δθ_k, homing fixes one knot per joint, gauge families G1–G5, excitation and rank criterion; interpolation bound ω h/2 and spacing table; marker-noise pose covariance, tracker-distortion rotation bias ≤ ω^trk_sys, repeatability, parameter covariance, noisy knots; error budget table and calibration-time model; improved FwdK/InvK, J_0 with |det| = |cos θ5|, convergence
  - report/sections/02_variables.tex: Conventions: shorthand for Section 3 (rob/trk superscripts, Δθ_k, δ_k, ω_k, R_k, R_w, p_cw, p_we)
  - docs/course_reference.md: Part 3.3 theory notation (shorthand, base fit, error-model terms, parameters, propagation, time and IK symbols)
  - AGENTS.md: section 6: added TBD line for this commit (Phase 3)
  - docs/progress_log.md: added this block
- Files: AGENTS.md, docs/course_reference.md, docs/progress_log.md, report/sections/02_variables.tex, report/sections/03_mathematical_approach.tex

### 5428df6 | 2026-10-26 15:50 | "Phase 4: student code, unit tests and executed notebook (single-axis plan, decoupled init, gauge from handout bounds)" | pushed
- Agent: Claude Code (Opus 5.5), branch assignment2-gy (new branch for this work, based on assignment2 at 30d8d49)
- Changes:
  - src/student/metrics.py: frame_error (rotation angle from log_so3, translation norm); summarize_errors (n, rms/mean/max of angle and position)
  - src/student/registration.py: register_points (centered SVD with reflection fix; rejects < 3 pairs, unequal lengths, collinear sets); average_frames (chordal mean projected to SO(3)); refine_marker_body (readings mapped back into the body frame and averaged, stored with update_marker_body)
  - src/student/workflow.py: measure_home_offsets (-mean of n homings); collect_calibration_data (repeats averaged per pose, invisible poses skipped and recorded; CalibrationData gains n_readings, skipped); estimate_base_frame (average of F_obs,j fwd_kins(theta_j)^-1); plan_calibration_poses with method 'single_axis' (default, handout method 1) and 'concurrent' (wrist/stage pairs swept together), knot stops at 100 mm / pi/4, repetitions per stop sized from desired_accuracy, visibility check with the worst-case base-pose margin; helpers joint_knots, readings_per_stop, estimate_plan_time
  - src/student/kinematics.py: ImprovedKinematics with piecewise-linear knot model of delta_theta_k (planner knots, home knot fixed by homing), tilts phi_2..6, tool twist, base twist; initial_estimate (decoupled closed form from single-axis sweeps: stage directions and joint values from translations, wrist axes and angles from relative rotations, pivot calibration for tool offset and wrist center); weighted least-squares fit over merged repeated commands; the G2+G3 gauge (rotation about d_1, not removed by homing) is fixed during the fit and then chosen as the midpoint of the interval allowed by the handout bounds (choose_gauge); Jacobian rank report with parameter stds; parameters_report
  - tests/test_student.py: TODO tests written (planner visibility/limits/knots/repetitions, synthetic fit recovery, refine_marker_body); new tests for the planner rejection, readings_per_stop, decoupled initial estimate and gauge choice; 44 passed
  - notebooks/assignment2_template.ipynb: Step 1 scene (robot at origin, side-view tracker, 74.9 mm tetrahedron mBee), Step 6 timing, Step 7 single_axis plan (comment explains the theta = 0 sweep base), Step 8 fit and ground-truth comparison, Steps 9-10 evaluation (greedy target order), summary table, multi-seed comparison of both plans; executed with outputs (all targets met, seeds 1-5)
  - AGENTS.md: section 7: Windows setup (conda env cis-a1, python path, Git Bash, autocrlf, missing tectonic/pdftoppm); section 6: Phase 4 checked, added TBD line for this commit
  - docs/progress_log.md: Pending merged into this block
- Files: AGENTS.md, docs/progress_log.md, notebooks/assignment2_template.ipynb, src/student/kinematics.py, src/student/metrics.py, src/student/registration.py, src/student/workflow.py, tests/test_student.py

### 1ed6048 | 2026-10-26 16:16 | "Tests: collect_calibration_data and estimate_plan_time" | pushed
- Agent: Claude Code (Opus 5.5), branch assignment2-gy
- Changes:
  - tests/test_student.py: test_collect_calibration_data_averages_readings_and_skips_invisible_poses (tracker shifted 800 mm: visible pose gives one sample averaged from 3 readings near the actual pose, invisible pose skipped after one reading with a warning, t_collect = motion time + readings, repeats < 1 rejected); test_estimate_plan_time_matches_the_simulated_clock (estimate equals the clock advance of collecting a plan); 46 passed
  - AGENTS.md: section 6: added TBD line for this commit
  - docs/progress_log.md: Pending merged into this block
- Files: AGENTS.md, docs/progress_log.md, tests/test_student.py

### 86379d8 | 2026-10-26 17:08 | "Report: Sections 4-7 (algorithm, program structure, validation, results)" | not pushed
- Agent: Claude Code (Opus 5.5), branch assignment2-gy
- Changes:
  - report/sections/04_algorithmic_approach.tex: Algorithmic Approach: scene design (incl. why no other marker body), homing, pose planning (knots, readings per stop, single-axis sweeps from theta = 0 and why, visibility margin, concurrent variant), data collection, decoupled initial estimate, weighted least-squares fit, rotation about d_1 chosen from the handout bounds (seven null directions, six removed by homing), improved FwdK/InvK, tracker-frame evaluation, execution-flow figure
  - report/sections/05_program_structure.tex: module table, hierarchy figure, runtime-function table, tests, outputs
  - report/sections/06_validation.tex: end-to-end metrics, supplied and own unit-test tables with purposes, 46 passed, limitations
  - report/sections/07_results.tex: calibration data and time, estimated parameters vs truth, seed-1 accuracy, five seeds and both plans, the handout's base-frame definition (achieved accuracy, met for seed 1 only)
  - report/sections/01_introduction.tex: section heading only, so that Sections 2-7 are numbered as the file names; body still to be written
  - report/main.tex: preamble: fn macro (\fn) for code names that break only after _ . / ,
  - audit against the handout, code and saved outputs: rotation R_trk,rob in the stage sweep equation, theta = 0 vs home reading (offset plus repeatability), plan time range, gauge wording, joint-offset labels (line value at 0 vs true c_k), test time
  - Note: Section 3 (teammate) still states that homing removes all gauges and 6+10+6 parameters; Section 4 follows the code (G2+G3 remains, 59 parameters)
  - Note: Section 7.4 (seeds 6-25) and 7.5 (base-frame metric) use separate verification runs, not saved notebook outputs
  - AGENTS.md: section 6: added TBD line for this commit
  - docs/progress_log.md: Pending merged into this block
- Files: AGENTS.md, docs/progress_log.md, report/main.tex, report/sections/01_introduction.tex, report/sections/04_algorithmic_approach.tex, report/sections/05_program_structure.tex, report/sections/06_validation.tex, report/sections/07_results.tex
