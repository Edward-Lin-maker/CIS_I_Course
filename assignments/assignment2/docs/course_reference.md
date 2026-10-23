# CIS I Course Reference (course_reference)

Three parts:
- **Part 1** Lecture notes, condensed (includes my interpolation-error guide)
- **Part 2** A1 report, condensed (format reference; full source in `docs/a1_report.tex`)
- **Part 3** A2 task, condensed + working understanding (living section; updated while writing the report's notation/math)

Authority: for task requirements, `docs/2026_assignment_2.pdf` (R. H. Taylor, *Assignment 2 – CIS I (601.455/655) Fall 2026*, October 15, 2026) is the source of truth.
Course repository: https://github.com/LCSR-CIIS/CIS_I_Course

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
- Other topics (not needed for A2): fluoroscope/C-arm dewarping, ultrasound probe calibration, Bayesian regression, neural nets.

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
- Optical tracking accuracy is about 0.35 mm RMS and requires line of sight. A2 needs only this background.

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

# Part 3 A2 task (condensed) + working understanding — LIVING SECTION

Page numbers refer to `docs/2026_assignment_2.pdf`. Notation follows the handout.

## 3.1 Handout, condensed

### Scenario (p1)
- "Kinematic calibration of a cartesian robot. The goal is to reach a specified accuracy within as short a time as possible."
- The simulator keeps a simulated elapsed time t_elap, updated each time the robot moves or the tracker samples.

### The Tracker (p1–3)
- Viewing volume: described as a "tetrahedral volume shown in Figure 2". The figure shows a truncated pyramid starting 100 cm from the camera, 120 cm deep, with a 100×100 cm near face and a 200×200 cm far face. These dimensions were read from the figure; verify against the PDF.
- Tracker pose: F*_tracker = F_tracker ΔF_tracker, ‖α_tracker‖₂ ≤ σ_Ta, ‖ε_tracker‖₂ ≤ σ_Tp. **This assignment assumes no jiggle: σ_Ta = σ_Tp = 0.**
- Marker body: mB = DefineMarkerBody({a_m,1, …, a_m,N}). Actual positions a*_m,k = a_m,k + Δa_m,k, ‖Δa_m,k‖ ≤ δ_markers. The estimate can be improved by averaging multiple observations and calling PreviousValues = UpdateMarkerBody(mB, {…}). The simulator keeps using a*_m,k.
- Measurement: b* = b + ε^trk_sys(b) + ε_b, with ε_b ~ N(0, σ_b² I), ‖ε^trk_sys(b)‖ ≤ δ^trk_sys, ‖∇ε^trk_sys‖ ≤ ω^trk_sys.
- Placement: PlaceMarkerBody(mB, F_mB) gives F*_mB = ΔF_mB F_mB (left-multiplied), ΔF_mB ≈ Frame(I + sk(α_mB), ε_mB), ‖α_mB‖₂ ≤ δ_mBa, ‖ε_mB‖₂ ≤ δ_mBe.
- API: trk = CreateTracker(F, {mB…}); AddMarkerBodies / RemoveMarkerBodies(trk, {…}); {F1…FN} = SampleMarkerBodies(trk) (costs Δt_samp per call); MostRecentObservedFrame(mB); MostRecentObservedMarkers(mB).
- Typical values: σ_Ta = 0.01, σ_Tp = 5 mm (set to 0 here); σ_b = 0.1 mm; Δt_samp = 0.03 s; δ^trk_sys ≤ 0.1 mm; ω^trk_sys ≤ 7.5×10⁻⁴. δ_markers, δ_mBa and δ_mBe are not specified in the handout.

### The Robot — kinematics and errors (p3)
- The robot is located at F_rob and consists of "a cartesian base and a spherical wrist with a modular tool holder". Units are mm and radians.
- Nominal kinematics:
  - F_ee(θ) = F_c(θ1, θ2, θ3) F_cw F_w(θ4, θ5, θ6) F_we
  - F_c = θ1 d1 + θ2 d2 + θ3 d3
  - F_w = R(n4, θ4) R(n5, θ5) R(n6, θ6)
  - F_cw = Frame(I, [500, 0, 0]ᵀ); F_we = Frame(I, [100, 0, 0]ᵀ)
  - (d1, d2, d3) = (x, y, z); (n1, n2, n3) = (x, y, z); notation d_{k+3} = n_k
- Range: (0, −300, 0) mm ≤ (θ1, θ2, θ3) ≤ (600, 300, 600) mm; (−0.75π, −0.75π, −π) ≤ (θ4, θ5, θ6) ≤ (0.75π, 0.75π, π).
- Actual kinematics: "The axes of F_c are not quite perpendicular, and the linear stages and revolute joints have some distortion and random error."
  - θ*_k = θ_k + Δθ^rob_k,rnd + Δθ^rob_k,sys, with Δθ^rob_k,rnd ~ N(0, σ²_k,rnd); State() returns θ_k.
  - ‖Δθ^rob_k,sys‖ ≤ δ^rob_k,sys and |dΔθ^rob_k,sys/dθ_k| ≤ ω^rob_k,sys ("Although it is small, the distortion is not negligible.")
  - d*_1 = d1; d*_k = R(φ_k) d_k ≈ d_k + sk(R(φ_k) d_k) for 2 ≤ k ≤ 6, ‖φ_k‖ ≤ φ_max.
  - F*_we = F_we ΔF_ee(η_ee), ‖α_ee‖ ≤ 0.01, ‖ε_ee‖ ≤ 0.5.

### The Robot — functions, homing, motion, parameters (p4–5)
- Functions:
  - F = FwdKins(θ); θ = InvKins(F); (θ, θ̇, …) = State(); F = CommandedPose()
  - Δt = MoveJoints(θ); Δt = MoveRobot(F), where MoveRobot(F) = MoveJoints(InvKins(F)) and CommandedPose(θ) = FwdKins(θ)
  - "You will be asked to implement an improved version of the kinematics function."
- Homing: θ_encoders = HomeRobot() moves to home, where θ*_k = 0, and returns the encoder values (those returned by State()).
- Motion: θ_k^min ≤ θ_k ≤ θ_k^max, |θ̇_k| ≤ θ̇_k^max, |θ̈_k| ≤ θ̈_k^max. Motion time = t_settle + the time for the slowest joint. The value of t_settle is not given in the handout.
- Creation: Rob = CreateRobot(F_rob, α^max_rob, ε^max_rob, θ^min, θ^max, t_settle, φ_max, σ_k,rnd, |θ̇^max|, |θ̈^max|). F*_rob = ΔF_rob F_rob (left-multiplied), ‖α_rob‖ ≤ α^max_rob, ‖ε_rob‖ ≤ ε^max_rob.
- Parameter values:

| Parameter | k = 1–3 (linear) | k = 4–6 (revolute) |
|---|---|---|
| σ_k,rnd | 0.005 mm | 0.0001 rad |
| σ_k,sys | 0.01 mm | 0.001 rad |
| δ^rob_k,sys | 0.2 mm | 0.01 rad |
| ω^rob_k,sys | 0.0005 | 0.00005 |
| \|θ̇^max\| | 50 mm/s | 0.1 rad/s |
| \|θ̈^max\| | 500 mm/s² | 1 rad/s² |

α^max_rob = 0.05 rad; ε^max_rob = 5 mm; φ_max = 0.02 rad.

### Calibration marker body mBee (p5)
- Only ONE special marker body can be created: mBee = CreateRobotCalibrationBody({a*_1, …, a*_N}). Its a*_k are the actual (exact) values, and its coordinate system corresponds exactly to F_ee.
- It cannot be redefined for a robot. ‖a*_k‖₂ ≤ 75 mm; a smaller size may be desirable, and the size is a design choice.
- AttachCalibrationMarker(Rob) and DetachCalibrationMarker(Rob). When attached, F_mBee = F_ee, and its workspace pose is F_rob F_mBee.

### Problem and a few hints (p5–7)
- Error definition: F*_ee = F_ee ΔF_ee, ΔF_ee ≈ Frame(I + sk(α_ee), ε_ee).
- Deliverables: F_ee = ImprovedFwdKins(θ) and θ = ImprovedInvKins(F_ee) over the robot's work volume, with these targets:
  - FwdK: ΔF = (F*_ee(θ))⁻¹ ImprovedFwdKins(θ); ‖α_FwdK‖ ≤ 10⁻³ rad, ‖ε_FwdK‖ ≤ 0.2 mm.
  - InvK: θ = ImprovedInvKins(F); ΔF = F⁻¹ FwdKins(θ); ‖α_InvK‖ ≤ 10⁻³ rad, ‖ε_InvK‖ ≤ 0.2 mm.
- Required steps:
  - define the tracking camera and its approximate pose;
  - create the robot and its approximate pose F_rob;
  - define marker bodies and their approximate placements;
  - define and implement a workflow for gathering and reducing data;
  - evaluate over the work volume and report accuracy statistics plus the time for calibration and for testing;
  - if the target is not met, report the accuracy achieved and how.
- Unit tests for the individual components, with description and results.
- "The first three joints are kinematically decoupled from the last three."
- Method 1, estimate the correct kinematic parameters:
  - (a) determine how close sample points must be for the desired accuracy (depends on δ^trk_sys, ω^trk_sys, δ^rob_k,sys, ω^rob_k,sys);
  - (b) go home, move along/about each individual axis while taking data, and return home after each axis;
  - (c) determine the angles between axes and the θ_k ↔ θ*_k transformation (interpolation scheme);
  - (d) write the corrected forward and inverse kinematics;
  - (e) report the updated parameters, compare them to ground truth in debugging runs, and do "bottom line" testing of a reasonably sampled portion of the workspace.
- Method 2, map the space and interpolate: needs many more data points and a dense random test sampling.
- Method 3: a combination of both.
- The program run time is limited to 10 minutes. Method 1 is strongly urged; Method 2 is more likely to hit the runtime limit.
- "This is a (somewhat) realistic design exercise." Design parameters feed the error budget. Part of the task is deciding which spec-sheet elements are relevant. The report must explain and justify the design approach and decisions.

### Repository (README of assignments/assignment2)
- Student code lives in `src/student/` (metrics, registration, workflow, kinematics), is driven by the notebook, and is tested with pytest.
- Handout names map to snake_case (CreateRobot → `simulation.create_robot`).
- The code depends on `../assignment1/src`.
- Ground truth (`*_truth`, `actual_*`, `ground_truth_parameters`) is for validation only.
- The report needs results tables for more than one seed and a Jacobian rank report justifying the parameterization.

## 3.2 Handout inconsistencies / typos (keep the original; flag in the report)
1. p3: "F_c(θ1, θs, θ3)" — θs is presumably θ2.
2. p3: (n1, n2, n3) = (x, y, z), but F_w uses n4, n5, n6; with d_{k+3} = n_k the intended reading is n4..6 = x, y, z.
3. p3: d*_k ≈ d_k + sk(R(φ_k) d_k) — the small-angle form is presumably d_k + sk(φ_k) d_k.
4. p3: F*_we = F_we ΔF_ee(η_ee) reuses the symbol ΔF_ee from p5's accuracy definition. In the report, write ΔF_we for the tool-mounting error.
5. p5: the InvK accuracy uses F⁻¹ FwdKins(θ). Presumably the actual kinematics F*_ee(θ) is intended; to be confirmed.
6. Error side: right-multiplied for tracker, F_we and F_ee; left-multiplied for F_mB and F_rob.
7. p1: the volume is called "tetrahedral", but Figure 2 shows a truncated pyramid.
8. Parameter table: σ_k,sys (0.01 mm / 0.001 rad) is listed, but the error model uses δ and ω only; its role is unclear.
9. Not specified in the handout: t_settle, δ_markers, δ_mBa, δ_mBe (check `src/simulation/constants.py`).

## 3.3 Working understanding (preliminary; confirm during line-by-line reading)
- Actual model, assembled from p3 (not written as one line in the handout): F*_ee(θ) = F*_c(θ*_1..3; d*_1..3) F_cw F*_w(θ*_4..6; n*_4..6) F*_we. F_cw is assumed exact because the handout lists no error for it.
- Error sources vs. targets:
  - Δθ_sys on the revolute joints (0.01 rad) is 10× the target, so it must be calibrated.
  - φ_k = 0.02 over 600 mm of travel gives ≈ 12 mm, the dominant error.
  - ΔF_we must be calibrated.
  - Δθ_rnd cannot be calibrated but is well below the targets.
- Measurement chain: F_trk,mBee = F_tracker⁻¹ F*_rob F*_ee(θ). F_tracker and F*_rob are nuisance parameters: estimate them jointly or eliminate them.

## 3.4 Error-budget notes (preliminary)
- Linear-joint Δθ_sys with linear interpolation: error ≤ ω h/2 = 5×10⁻⁴ h/2. With h = 200 mm this is 0.05 mm, so 4–7 samples per 600 mm axis are enough.
- Wrist Δθ_sys up to 0.01 rad exceeds 10⁻³, so it must be calibrated. Its interpolation error is tiny: ω h/2 = 1.25×10⁻⁵ rad at h = 0.5 rad.
- Tracker systematic error between two points: ≤ min(2δ, ω_trk d) = min(0.2 mm, 7.5×10⁻⁴ d). Long baselines use up budget, so measure near the center of the volume.
- Noise: σ_b = 0.1 mm; use many markers and repeated samples (σ/√n). Sampling is cheap (0.03 s); motion dominates the time (600 mm takes ≥ 12 s).

## 3.5 Report notation / math progress (updated while writing)
- (empty — fill after the line-by-line reading and derivations)
