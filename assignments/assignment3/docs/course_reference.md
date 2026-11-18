# CIS I Course Reference - Assignment 3

Part 1: lecture reference. Part 2: A1 report format. Part 3: A2 distilled methods and lessons. Part 4: A3 task, source discrepancies and living notation.

Assignment-specific authority is `docs/2026_assignment_3.pdf`. Historical A1/A2 content is reference only.

---

# Part 1 Lecture notes (condensed)

## 1.0 Frames and basic operations (frames.pdf)
- F = Frame(R, p); F·b = Rb + p; F⁻¹ = Frame(Rᵀ, −Rᵀp); F1F2 = Frame(R1R2, R1p2 + p1). F_{x,y}: pose of y relative to x.
- sk(a)v = a × v. Small rotation: ΔR(α) ≈ I + sk(α). R sk(a) Rᵀ = sk(Ra); R(a × b) = R sk(−b) a. Second-order terms in small quantities are dropped.

## 1.1 Rigid 3D-3D registration (rigid3d3dcalculations.pdf)
- Point cloud to point cloud rigid registration: minimize Σ‖R a_k + p − b_k‖².
- Direct technique (SVD, Arun): centroids ā, b̄; ã = a − ā, b̃ = b − b̄; H = Σ ã b̃ᵀ; H = USVᵀ; R = VUᵀ (if det R = −1, flip the last column of V); p = b̄ − Rā.
- Quaternion method for R (Horn): G = [[tr H, Δᵀ], [Δ, H + Hᵀ − tr(H) I]], Δ = [H23 − H32, H31 − H13, H12 − H21]ᵀ; the unit quaternion q is the eigenvector of the largest eigenvalue.
- Direct iterative approach for rigid frame: least-squares solve sk(−a_k) α + ε ≅ b_k − a_k, set ΔF = Frame(R(α), ε), update F ← ΔF·F.
- Also covered: registration from line pairs, rotation axis/angle ↔ rotation matrix ↔ unit quaternion.

## 1.2 Least squares and error propagation (leastsquaresreview.pdf, frames.pdf)
- Linear least squares Ax ≅ b via SVD or Householder (QR). Least squares adjustment (nonlinear): J·Δq ≅ v − G(q), q ← q + Δq, iterate to convergence.
- Point error: Δv ≈ R(Δb + α × b + Δp) = [R | R | R sk(−b)]·[Δb; Δp; α].
- Composition F3 = F1F2: α3 ≈ R2ᵀα1 + α2, ε3 ≈ ε2 − R2ᵀ sk(p2) α1 + R2ᵀ ε1. Inverse: α_inv = −Rα, ε_inv = −Rε − R sk(Rᵀp) α.
- Covariance: Cov(Ax + c) = A C Aᵀ. Fusion of independent estimates: E[x|·] = μx + Cxx(Cxx + Cyy)⁻¹(μy − μx).
- Probabilistic estimation of a pose: ε_k = A_k η, A_k = [−sk(F·b_k) | I]; pose confidence C_F = (Σ G_k⁻¹)⁻¹.

## 1.3 Calibration (calibration.pdf)
- Two approaches:
  - **Parameter estimation**: compare observed system performance to a reference standard ("ground truth"); compute the parameters of a mathematical model ("model of reality") that minimize the residual error.
  - **Mapping the space**: interpolate residual errors; model correction lookup table.
- Example "Robodoc Wrist Calibration": kinematic model → linearization → linear least squares parameter estimation. 2-link case: linearize in (a1, a2, θ1, θ2) and solve with the Jacobian.
- Pivot calibration: [R_j | −I]·[b_tip; p_pivot] ≅ −p_j.
- Calibrating trackers to robots and similar "AX = XB" problems: A_k = F_hw,k F_hw,0⁻¹, B_k = F_rc,k F_rc,0⁻¹.
  - Rotation: q_A q_X = q_X q_B ⇒ M q = 0, with M = [[s_A − s_B, −(v_A − v_B)ᵀ], [v_A − v_B, (s_A − s_B) I + sk(v_A + v_B)]]. Stack M over k, take the SVD, and use the 4th column of V. (A weaker alternative: solve R_X β_k = α_k with axis-angle vectors.)
  - Translation: (R_A,k − I) p_X ≅ R_X p_B,k − p_A,k.
- Other lecture topics: fluoroscope/C-arm dewarping, ultrasound probe calibration, Bayesian regression, neural nets.

## 1.4 Interpolation and deformations: a short cookbook (interpolationreview.pdf)
- Linear interpolation (barycentric form); bilinear; N-linear interpolation: weights W_i = Π_r b_{i_r}(θ_r), b0 = 1 − t, b1 = t. Barycentric interpolation: [a…; 1…] λ = [a; 1].
- Bezier and Bernstein polynomials: B_{N,k}(v) = C(N,k) (1 − v)^{N−k} v^k, v ∈ [0, 1]; first ScaleToBox, u = (x − min)/(max − min). de Casteljau algorithm.
- 3D distortion correction: F_ijk = B_{5,i}(u_x) B_{5,j}(u_y) B_{5,k}(u_z); least-squares fit of c_ijk (216 coefficients × 3). On a regular grid the fit can be split into two smaller LS steps.
- B-splines (uniform cubic, local support, de Boor). Scattered data: Shepard; radial basis function interpolation (choice of RBF constants matters).
- Linear interpolation with uncertainty (see 1.5).

## 1.5 My interpolation error and uncertainty guide (interpolation_guide.pdf, condensed)
- 1D: λ = (x − x1)/h. If |f′| ≤ φ, the deterministic error satisfies |e_det| ≤ 2φhλ(1 − λ) ≤ φh/2.
- With noisy samples: E[e] = e_det; Var = (1 − λ)²σ1² + λ²σ2² + 2λ(1 − λ)c12; MSE = e_det² + Var.
- ND scalar: if |∂_r f| ≤ φ_r, then |e| ≤ 2 Σ_r φ_r h_r θ_r(1 − θ_r) ≤ ½ Σ_r φ_r h_r. If ‖∇f‖ ≤ φ, then |e| ≤ φ √(Σ_r θ_r(1 − θ_r) h_r²) ≤ (φ/2) √(Σ_r h_r²) (by Jensen). Var = Σ_i Σ_j W_i W_j c_ij = wᵀCw.
- 1D vector: ‖e‖ ≤ φh/2; Cov = (1 − λ)²C11 + λ²C22 + λ(1 − λ)(C12 + C12ᵀ).
- ND vector: replace the bounds above with ‖∂f/∂x_r‖ or ‖J‖₂; Cov = Σ_i Σ_j W_i W_j C_ij = H C Hᵀ.

## 1.6 Localizers (localizers.pdf, background only)
- Optical tracking accuracy is about 0.35 mm RMS and requires line of sight. Assignment-specific noise values must come from the current handout and code.

---

# Part 2 A1 report (condensed format reference)

## 2.1 Section structure
- Title page: title, team members, student IDs, contact, academic-integrity statement box.
- Table of contents.
- 1 Introduction.
- 2 Mathematical Approach: Notation and frame conventions → design subsections → Measurement model and origins of uncertainty → algorithm derivations → Error and covariance.
- 3 Algorithmic Approach: one subsection per code cell, each with a "Main tasks" paragraph, a function table, and a roman-numeral step list; ends with a function-level execution-flow figure.
- 4 Program Structure: file/module table, program hierarchy figure, runtime function table, validation/sensitivity helper table, test class table, program outputs.
- 5 Validation Approach: end-to-end accuracy → Unit Test A/B (subsections A.1–A.5, B.1–B.7, with sensitivity plots) → Limitations.
- 6 Result.
- 7 AI Assistance and Use of Tools.
- References.

## 2.2 Preamble
```latex
\documentclass[11pt]{article}
\usepackage[T1]{fontenc}\usepackage{amsmath,amssymb,bm}\usepackage[margin=1in]{geometry}
\usepackage{booktabs,longtable,array}\usepackage{graphicx}\usepackage{float}
\usepackage{tikz}\usetikzlibrary{arrows.meta}\usepackage{pgfplots}\pgfplotsset{compat=1.18}
\usepackage[superscript]{cite}\usepackage[hidelinks]{hyperref}\usepackage{tocloft}
\newcommand{\vct}[1]{\bm{#1}}\newcommand{\sk}{\operatorname{sk}}\newcommand{\Cov}{\operatorname{Cov}}
\newcommand{\Frame}{\operatorname{Frame}}\newcommand{\diag}{\operatorname{diag}}\newcommand{\tr}{\operatorname{tr}}
\newcommand{\rank}{\operatorname{rank}}\newcommand{\Fun}[1]{\operatorname{#1}}\newcommand{\norm}[1]{\left\|#1\right\|_2}
\setcounter{tocdepth}{2}\cftpagenumbersoff{section}\cftpagenumbersoff{subsection}\cftpagenumbersoff{subsubsection}
```

## 2.3 Notation (A1 wording)
- "Bold lowercase symbols denote three-dimensional column vectors. A star denotes hidden physical ground truth; a hat denotes an estimate." Unmarked symbols are nominal.
- Subscripts m, k, j: marker body, marker, observation. Superscript (r): refinement iteration. Lengths in mm, angles in rad.
- F = Frame(R, p), Fx = Rx + p, F⁻¹y = Rᵀ(y − p). "The translation is the source-frame origin expressed in the destination frame."
- Error-multiplication side follows the handout: right-multiplied F* = FΔF for tracker/cal/test; left-multiplied F* = ΔF·F for PlaceMarkerBody.

## 2.4 Table styles
Common pattern: `\begingroup\small` (or `\footnotesize`/`\scriptsize` for wide tables) + `longtable` + booktabs; the header is repeated in `\endfirsthead` and `\endhead`; rows are separated by `\midrule`; short captions; labels `tab:xxx`.

| Table | Columns | Widths (\textwidth) |
|---|---|---|
| Symbols (tab:symbols) | Symbol \| Meaning \| Repository variable | 0.20 / 0.43 / 0.28 |
| Frames (tab:frames) | Frame and direction \| Nominal \| Estimated \| Actual \| Relation | 0.16/0.17/0.19/0.18/0.20, ragged-right `>{\raggedright\arraybackslash}p{}`, `\tabcolsep=3pt`, footnotesize |
| Error limits (tab:errorlimits) | Quantity \| Bound or model \| Value | 0.22 / 0.38 / 0.31 |
| Algorithm functions (one per cell) | Code cell \| Function \| Inputs \| Outputs | 0.09 / 0.28 / 0.25 / 0.27 |
| File/module | Location \| Responsibility | 0.32 / 0.59 |
| Runtime functions | Cell \| Function \| Inputs \| Output and purpose | 0.055/0.225/0.255/0.335, scriptsize |
| Results | `table[H]` + `tabular{lrrrr}`, e.g. N \| Mean \| RMSE \| Maximum \| Within target | — |

Cell conventions:
- Missing values are written "numerical values not specified" or "None specified."
- Ground-truth quantities are marked "validation only".
- Functions and paths use `\path{}`; code variables use `\texttt{}`.

## 2.5 Figures and writing habits
- Diagrams and flow charts in TikZ with `figure[H]`; sensitivity plots in pgfplots `axis`, with data taken from saved notebook outputs.
- References in `thebibliography`, citing pages and slides (e.g. "pp. 2--7", "slides 7--15").
- The final section states honestly what the AI tools did and where the data came from.
- Compiled with LaTeX or Tectonic.

---

# Part 3 A2 report (condensed reference, not A3 requirements)

Source: preserved `assignment2` branch at `06ad292`; complete report source and signed PDF remain on that branch. These are historical methods and lessons, not A3 parameter values.

## 3.1 Mathematical organization
- State the desired prediction and measured quantities, define frame directions and error sides, then introduce only parameters needed by the current step.
- Explain the initialization pipeline before collecting detailed error analysis in one place. Each least-squares step identifies inputs, unknowns, residual, solver, and outputs.
- Distinguish physical ground truth (*), observations (obs), parameter estimates (est), and model-predicted poses (hat). This project convention supersedes A1's historical hat notation.
- A2 used single-joint geometry for initial axes/travels, homing to constrain distortion offsets, a wrist-center solve for initialization, then a joint weighted pose fit. These robot-specific steps do not transfer to surface ICP.
- Carry exact relationships before approximations; identify what an approximation drops, its role, and where its impact is evaluated.

## 3.2 Observability and error lessons
- A2's fitted tracker prediction was a product of an estimated base transform and internal forward kinematics. A simultaneous base turn and opposite internal-model turn left the product unchanged. Small measurement residuals did not certify the separate factors.
- A2 fixed a coordinate freedom and constrained constant joint distortions using homing; its saved numerical residual Jacobian had rank 59/59 after those constraints. This count is specific to that model and sampling, not an A3 rank target.
- For A3, analyze the identifiability of the selected registration model and sampling geometry on their own; do not carry A2's gauge, parameter count, or noise scales into A3.
- Distinguish random noise, shared reference errors, systematic errors, and model mismatch. More samples do not automatically remove the latter three.
- A2 averaging combined multiple arrivals that could resample joint noise; this was not equivalent to repeated stationary tracker readings. State exactly what is repeated in A3.

## 3.3 Validation and reproducibility lessons
- Use independent analytic answers and synthetic data, not only data generated and evaluated by the same model implementation.
- Test nominal/noiseless cases, noisy cases, boundary cases, degenerate geometry, invalid inputs, and convergence failures for major functions.
- A2 ultimately had 81 tests, including forward/inverse kinematics and initialization degeneracies. These are examples of coverage, not A3 tests to copy.
- Sensitivity experiments varied one controlled factor, retained seeds/raw outputs, and separated simulation time from actual runtime.
- State the exact error transform, evaluation frame, target set, statistic, and denominator. Measurement residuals and physical target errors may differ substantially.
- Match report tables/figures to saved notebook outputs; record seed, environment, timing scope, and failed runs. An archived run is not a newly executed run.
- Clean-install and run the submission end to end, with included data and documented repository dependencies. Preserve signed PDFs; recompilation does not preserve handwritten signatures.

## 3.4 Report structure and reuse boundaries
- Keep the A1-derived preamble, frame notation tables, function input/output tables, pipeline diagrams, and independent test/sensitivity explanations.
- A2 sections were Introduction; Variables and Notation; Mathematical Approach; Algorithmic Approach; Program Structure; Validation Approach; Results. A3 additionally has explicit AI/tools and contributions sections.
- Reuse explanatory structure, not old numerical results, dimensions, thresholds, robot assumptions, or claims of completed A3 validation.

---

# Part 4 A3 task and working reference

## 4.1 Authority and sources
- Requirements: `docs/2026_assignment_3.pdf`, R. H. Taylor, October 26, 2026, pp. 1-8.
- Starter behavior/interfaces: course main `d91ea42`, `README.md`, `src/session.py`, `src/mesh.py`, `src/student/report.py`, notebook and tests.
- A1 rubric photos: `docs/rubric1.jpg` through `rubric4.jpg`; transferable checklist in `docs/report_guidelines.md`. The photos are not an official A3 rubric.

## 4.2 Handout condensed
- Goal (pp. 4-7): estimate F_reg mapping reference-body coordinates to CT coordinates from tracked pointer samples on quasi-planar femur patches; explain pointer/reference-body geometry and ergonomics. Manufactured marker/tip geometry is exact for this scenario.
- Initial registration error (p. 4): left perturbation with rotation norm <= 0.2 rad and translation norm <= 10 mm.
- Use ICP or justify another method; explain sample selection and outlier rejection (p. 7). Pointer placement has outlier probability 0.1 and tilt norm <= 0.1 rad.
- Final calibrated tracking values (p. 7): systematic bound 0.003 mm and per-coordinate marker noise sigma_b = 0.01 mm; earlier typical values are not the final scenario values.
- Handout target (p. 7): sigma_reg <= 1 mm; TRE evaluated over mesh vertices (footnote and p. 8). Do not silently reinterpret this as a maximum-error requirement.
- Report patch IDs/counts; final valid/rejected sample lists; residual-norm mean, standard deviation, maximum and 90th percentile; total simulated time and actual computation time (pp. 7-8).
- Registration uncertainty and predicted TRE distribution are optional in the handout (p. 8). Explain FRE versus TRE; no claim that small residuals guarantee small TRE.
- Execution <= 10 minutes; simulated time has no fixed upper limit but needs a realistic surgical rationale (p. 8).
- General report/code requirements (pp. 1-3): design/specifications/ergonomics; quantitative sketches/tables and rationale; defined variables, cited equations and derivations, corner cases; reproducible algorithm descriptions and control/data flow; component and end-to-end validation; achieved-performance table; AI/code credits and prompts; contributions; signed cover.

## 4.3 Starter code scope
- Simulation runs on the course server. `Session` is the interface; do not implement a private simulator or rely on server internals.
- Keep grading signatures `design_scene()` and `run_registration(session, mesh, boxes)`.
- `Observation.frame` maps body to tracker; `Observation.markers` are tracker-coordinate points (`src/session.py`).
- `RegistrationReport` stores F_reg, patches, sample decisions, residual statistics, both times, ICP iterations/convergence, eta_reg and predicted_tre (`src/student/report.py`).
- Keep the full repository: types are in root `data_types/`, tracker/frustum imports come from A1. Do not copy A1 noise constants into A3.
- Practice-only `evaluate_tre` and `true_outliers` are validation tools. Never call them from `run_registration` or use them for design/estimation decisions.
- Student modules: closest_point, icp, uncertainty, workflow. No implementation has been added during setup.

## 4.4 Source discrepancies (unresolved; do not silently fix)
| Item | Handout | Starter README | Handling |
|---|---|---|---|
| TRE goal | 1 mm (p. 7) | 2 mm | State both sources; use handout goal for report requirements pending clarification. |
| Calibrated marker noise sigma_b | 0.01 mm (p. 7) | 0.1 mm | Keep separate; remote server noise is not verified by reading the client. |
| Tracker systematic bound | 0.003 mm (p. 7) | 0.03 mm | Keep separate; do not change client or infer hidden server values. |
| F_reg direction in pointer-placement equations | Text says reference -> CT, but composition uses F_reg where inverse is needed (p. 7) | Explicitly documents inverse correction | Use declared frame directions when deriving; preserve original and seek confirmation before registering a formal handout correction. |
| Uncertainty | Optional (p. 8) | Student uncertainty module/task required | Track both; plan to satisfy starter interface as well as handout. |
| Submission folder | `assignment1/` (p. 3) | A3 folder/interfaces | Record discrepancy; use actual A3 code layout pending clarification. |

## 4.5 Report notation (living section)
Not yet defined. Add only primary report symbols, meanings, frame directions and code mappings when the notation section is written. Keep temporary derivation symbols in LaTeX.

## 4.6 Confirmed clarifications and stage conclusions
None yet. Distinguish source facts above from future user-confirmed conclusions.
