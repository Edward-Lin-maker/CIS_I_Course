# Progress Log - CIS I Assignment 3

Fresh log for A3. Complete A2 work remains on the assignment2 and assignment2_code branches; the A2 working folder matches course main.

## Pending
- 11-18 17:00 | Claude | src/student/geometry.py, design.py | add frame/rotation-vector helpers and Step 1 design values with tip-error analysis
- 11-18 17:00 | Claude | src/student/closest_point.py | exact vectorised point-triangle closest point and KD-tree pruned closest point on mesh
- 11-18 17:00 | Claude | src/student/icp.py | weighted SVD registration, robust coarse registration, point-to-plane ICP with MAD rejection, multi-start selection
- 11-18 17:00 | Claude | src/student/uncertainty.py | least-squares covariance of eta_reg and predicted TRE over mesh vertices
- 11-18 17:00 | Claude | src/student/workflow.py | design_scene, greedy TRE-optimal patch plan, averaged collection, refill round, run_registration report
- 11-18 17:00 | Claude | validation/ | validation-only offline simulator and multi-seed experiment script (results in validation/results)
- 11-18 17:00 | Claude | tests/test_student.py | implement the two TODO tests and add 15 component/edge-case/end-to-end tests (22 pass)
- 11-18 17:00 | Claude | notebooks/assignment3_template.ipynb | fill design cell, add session backend switch, multi-seed table; executed with offline backend
- 11-18 17:30 | Claude | validation/run_remote.py | script to run run_registration on the course server for practice seeds (token via A3_COURSE_TOKEN)
- 11-18 17:45 | Claude | notebooks/assignment3_template.ipynb, validation/results/remote_* | ran seeds 1-5 on the course server and re-executed the notebook with the remote backend (token not stored)

## Commits

### fb6ca0f | 2026-11-18 12:26 | "Setup: initialize Assignment 3 references and report skeleton" | pushed
Agent: Codex

Changes:
- Initialize Assignment 3 on course main d91ea42 without modifying starter code.
- Migrate the A3 handout and four A1 rubric photographs; retain an A1 format reference and distill A2 methods and validation lessons.
- Add project rules, transferable rubric guidance, source-discrepancy notes and an AI assistance record.
- Create nine empty report chapters, a fresh log and local build ignore rules; verify warning-free compilation and source integrity.
- Remove residual A2 build/cache files and the clean auxiliary worktree; preserve the existing A2 branches and remote history.

Files: AGENTS.md, CLAUDE.md, .gitignore, docs/, report/main.tex, report/sections/, report/figures/.gitkeep.

### 6ee2f0a | 2026-11-18 12:55 | "docs: add workspace guide and clarify design requirements" | pushed
Agent: Codex

Changes:
- Add a teammate workspace guide describing file ownership, differences from course main, report structure and assistant workflow.
- Separate explicit A3 design requirements from A1-informed presentation suggestions; update the rule-file navigation and wording.

Files: docs/workspace_guide.md, docs/report_guidelines.md, AGENTS.md, docs/progress_log.md.
