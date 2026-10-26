# CIS I Course Reference (course_reference)

Three parts:
- **Part 1** Lecture notes, condensed (includes my interpolation-error guide)
- **Part 2** A1 report, condensed (format reference; full source in `docs/a1_report.tex`)
- **Part 3** A2 task, condensed + working understanding (living section): 3.1 handout condensed, 3.2 handout typos, 3.3 report notation, 3.4 clarifications and interim conclusions

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

# Part 3 A2 task (condensed) + clarifications — LIVING SECTION

Page numbers refer to `docs/2026_assignment_2.pdf`. Notation follows the handout.

## 3.1 Handout, condensed

### Scenario (p1)
- "Kinematic calibration of a cartesian robot. The goal is to reach a specified accuracy within as short a time as possible."
- The simulator keeps a simulated elapsed time t_elap, updated each time the robot moves or the tracker samples.

### The Tracker (p1–3)
- Viewing volume: described as a "tetrahedral volume shown in Figure 2" (see 3.2 #7). The figure shows a truncated pyramid starting 100 cm from the camera, 120 cm deep, with a 100×100 cm near face and a 200×200 cm far face. Matches `Tracker.FRUSTUM_*` in the code (near 1000 mm, far 2200 mm, half-width 500–1000 mm).
- Tracker pose: F*_tracker = F_tracker ΔF_tracker, ‖α_tracker‖₂ ≤ σ_Ta, ‖ε_tracker‖₂ ≤ σ_Tp. **This assignment assumes no jiggle: σ_Ta = σ_Tp = 0.**
- Marker body: mB = DefineMarkerBody({a_m,1, …, a_m,N}). Actual positions a*_m,k = a_m,k + Δa_m,k, ‖Δa_m,k‖ ≤ δ_markers. The estimate can be improved by averaging multiple observations and calling PreviousValues = UpdateMarkerBody(mB, {…}). The simulator keeps using a*_m,k.
- Measurement: b* = b + ε^trk_sys(b) + ε_b, with ε_b ~ N(0, σ_b² I), ‖ε^trk_sys(b)‖ ≤ δ^trk_sys, ‖∇ε^trk_sys‖ ≤ ω^trk_sys.
- Placement: PlaceMarkerBody(mB, F_mB) gives F*_mB = ΔF_mB F_mB (left-multiplied), ΔF_mB ≈ Frame(I + sk(α_mB), ε_mB), ‖α_mB‖₂ ≤ δ_mBa, ‖ε_mB‖₂ ≤ δ_mBe.
- API: trk = CreateTracker(F, {mB…}); AddMarkerBodies / RemoveMarkerBodies(trk, {…}); {F1…FN} = SampleMarkerBodies(trk) (costs Δt_samp per call); F_m = MostRecentObservedFrame(mB) (body pose relative to the tracker); {b_m,1, …, b_m,N} = MostRecentObservedMarkers(mB) (individual marker readings, tracker frame; the handout writes a here, see 3.2 #10). Both return the last SampleMarkerBodies result and cost no time.
- Typical values: σ_Ta = 0.01, σ_Tp = 5 mm (set to 0 here); σ_b = 0.1 mm; Δt_samp = 0.03 s; δ^trk_sys ≤ 0.1 mm; ω^trk_sys ≤ 7.5×10⁻⁴. δ_markers, δ_mBa and δ_mBe are not specified in the handout.

### The Robot — kinematics and errors (p3)
- The robot is located at F_rob and consists of "a cartesian base and a spherical wrist with a modular tool holder". Units are mm and radians.
- Nominal kinematics:
  - F_ee(θ) = F_c(θ1, θ2, θ3) F_cw F_w(θ4, θ5, θ6) F_we
  - F_c = θ1 d1 + θ2 d2 + θ3 d3 (handout writes F_c(θ1, θs, θ3), see 3.2 #1)
  - F_w = R(n4, θ4) R(n5, θ5) R(n6, θ6)
  - F_cw = Frame(I, [500, 0, 0]ᵀ); F_we = Frame(I, [100, 0, 0]ᵀ)
  - (d1, d2, d3) = (x, y, z); (n1, n2, n3) = (x, y, z) [read as n4..6, see 3.2 #2]; notation d_{k+3} = n_k
- Range: (0, −300, 0) mm ≤ (θ1, θ2, θ3) ≤ (600, 300, 600) mm; (−0.75π, −0.75π, −π) ≤ (θ4, θ5, θ6) ≤ (0.75π, 0.75π, π).
- Actual kinematics: "The axes of F_c are not quite perpendicular, and the linear stages and revolute joints have some distortion and random error."
  - θ*_k = θ_k + Δθ^rob_k,rnd + Δθ^rob_k,sys, with Δθ^rob_k,rnd ~ N(0, σ²_k,rnd); State() returns θ_k.
  - ‖Δθ^rob_k,sys‖ ≤ δ^rob_k,sys and |dΔθ^rob_k,sys/dθ_k| ≤ ω^rob_k,sys ("Although it is small, the distortion is not negligible.")
  - d*_1 = d1; d*_k = R(φ_k) d_k ≈ d_k + sk(R(φ_k) d_k) [use d_k + sk(φ_k) d_k, see 3.2 #3] for 2 ≤ k ≤ 6, ‖φ_k‖ ≤ φ_max.
  - F*_we = F_we ΔF_ee(η_ee) [written ΔF_we, see 3.2 #4], ‖α_ee‖ ≤ 0.01, ‖ε_ee‖ ≤ 0.5.

### The Robot — functions, homing, motion, parameters (p4–5)
- Functions:
  - F = FwdKins(θ); θ = InvKins(F); (θ, θ̇, …) = State(); F = CommandedPose()
  - Δt = MoveJoints(θ); Δt = MoveRobot(F), where MoveRobot(F) = MoveJoints(InvKins(F)) and CommandedPose(θ) = FwdKins(θ) [CommandedPose() = FwdKins(θ_cmd), see 3.2 #13]
  - "You will be asked to implement an improved version of the kinematics function."
- Homing: θ_encoders = HomeRobot() moves to home, where θ*_k = 0, and returns the encoder values (those returned by State()).
- Motion: θ_k^min ≤ θ_k ≤ θ_k^max, |θ̇_k| ≤ θ̇_k^max (handout: θ_k|θ̇_k|, see 3.2 #14), |θ̈_k| ≤ θ̈_k^max. Motion time = t_settle + the time for the slowest joint. The value of t_settle is not given in the handout.
- Creation: Rob = CreateRobot(F_rob, α^max_rob, ε^max_rob, θ^min, θ^max, t_settle, φ_max, σ_k,rnd, |θ̇^max|, |θ̈^max|). F*_rob = ΔF_rob F_rob (left-multiplied; handout formula garbled, see 3.2 #12), ‖α_rob‖ ≤ α^max_rob, ‖ε_rob‖ ≤ ε^max_rob.
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
- AttachCalibrationMarker(Rob) and DetachCalibrationMarker(Rob). When attached, F_mBee = F_ee, and its workspace pose is F_rob F_mBee [actual: F*_rob F*_ee(θ*), see 3.2 #15].

### Problem and a few hints (p5–7)
- Error definition: F*_ee = F_ee ΔF_ee, ΔF_ee ≈ Frame(I + sk(α_ee), ε_ee).
- Deliverables: F_ee = ImprovedFwdKins(θ) and θ = ImprovedInvKins(F_ee) over the robot's work volume, with these targets:
  - FwdK: ΔF = (F*_ee(θ))⁻¹ ImprovedFwdKins(θ); ‖α_FwdK‖ ≤ 10⁻³ rad, ‖ε_FwdK‖ ≤ 0.2 mm.
  - InvK: θ = ImprovedInvKins(F); ΔF = F⁻¹ FwdKins(θ) [F*_ee(θ), see 3.2 #5]; ‖α_InvK‖ ≤ 10⁻³ rad, ‖ε_InvK‖ ≤ 0.2 mm.
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
  - (d) write the corrected forward and inverse kinematics [see 3.2 #18];
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
1. p3: "F_c(θ1, θs, θ3)" → F_c(θ1, θ2, θ3). Code: `src/robot.py` `fwd_kins` uses p_c = (θ1, θ2, θ3).
2. p3: (n1, n2, n3) = (x, y, z) → (n4, n5, n6) = (x, y, z), since F_w uses n4, n5, n6 (d_{k+3} = n_k). Code: `Robot.AXES` = x, y, z twice; `fwd_kins` uses Rot('x', θ4) Rot('y', θ5) Rot('z', θ6).
3. p3: d*_k ≈ d_k + sk(R(φ_k) d_k) → d*_k ≈ d_k + sk(φ_k) d_k (= d_k + φ_k × d_k). As written, a 3×3 matrix is added to a vector, and R(φ_k) d_k is d*_k itself. The exact form d*_k = R(φ_k) d_k is what the code uses (`exp_so3(phi_k) @ d_k` in `create_robot`).
4. p3: F*_we = F_we ΔF_ee(η_ee) reuses the symbol ΔF_ee from p5's accuracy definition. In the report, write ΔF_we for the tool-mounting error.
5. p6: the InvK accuracy ΔF = F⁻¹ FwdKins(θ) → F⁻¹ F*_ee(θ), the pose actually reached. Notebook Step 10: θ = `inv_kins(...)`, `rob.move_joints(θ)`, then the target is compared with `mbee_placed.actual_placement`. With the nominal FwdKins the measure would only test FwdKins/InvKins consistency.
6. Error side: right-multiplied for tracker, F_we and F_ee; left-multiplied for F_mB and F_rob.
7. p1: the volume is called "tetrahedral" → truncated pyramid, as drawn in Figure 2 and implemented by `Tracker.is_visible` / `Tracker.FRUSTUM_*`.
8. p4–5: σ_k,sys, δ_k,sys and ω_k,sys have values in the p5 table but are missing from the p4 CreateRobot signature, and the handout gives σ_k,sys no role in its error model. Code: `create_robot` adds `sigma_sys`, `delta_sys`, `omega_sys` (plus `name`, `seed`); σ_sys is the ripple amplitude in Δθ_sys = c + sθ + σ sin(Aθ + B) (code-only model, `src/simulation/robot.py`).
9. Not specified in the handout: t_settle (code: `T_SETTLE = 0.05` s), δ_markers, δ_mBa, δ_mBe (code reuses A1 values), the minimum number of mBee markers (code: ≥ 3), and that mBee starts attached (code). See `src/simulation/constants.py`, `calibration_body.py`.
10. p2: {a_m.1, …, a_m,N} = MostRecentObservedMarkers(mB) → {b_m,1, …, b_m,N}. The function returns the observed marker positions in the tracker frame, not the body-frame a_m,k (A2 `src/simulation/marker_body.py` docstring says b). To get body-frame values, compute F_m⁻¹ b_m,k yourself.
11. p2 minor notation (no effect on the math): a_m.1 → a_m,1; "estimate of a_m,b" → a_m,k; F_mb, α_mb, ε_mb → F_mB, α_mB, ε_mB; stray "−" in "ω^trk_sys − ≤ 7.5×10⁻⁴".
12. p4: F*_rob = ΔF_rob F_rob = Frame(Rot(α_rob), ε_rob) → F*_rob = ΔF_rob F_rob with ΔF_rob = Frame(Rot(α_rob), ε_rob). As written, the actual base pose equals the small perturbation itself. Code: `F_rob_actual = … perturb(xi_rob)  # F*_rob = dF_rob F_rob` (`src/simulation/robot.py`).
13. p4: the function table has CommandedPose() (no argument), the implementation line has CommandedPose(θ) = FwdKins(θ) → CommandedPose() = FwdKins(θ_cmd), where θ_cmd is the last commanded joint vector (= θ from State()). Code: `commanded_pose()` returns `fwd_kins(self.theta_cmd)` (`src/robot.py`).
14. p4: θ_k|θ̇_k| ≤ θ̇_k^(max) → |θ̇_k| ≤ θ̇_k^(max). The product has the wrong units (mm²/s vs mm/s) and does not match |θ̈_k| ≤ θ̈_k^(max) or the p5 table. Code: `motion_time` uses θ̇_max as a plain speed limit (`src/robot.py`).
15. p5 / Figure 1: F_mBee breaks the single-subscript convention of p2 (F_mB = pose relative to the workspace; F_m = observed pose relative to the tracker), under which F_mBee would be relative to the workspace. The handout uses it in two other ways: p5 text "relative to the robot base … F_mBee = F_ee" (base-relative); Figure 1 arrow from the tracker (tracker-relative). p5 also writes the workspace pose without stars (F_rob F_mBee); the actual pose is F*_rob F*_ee(θ*) (`mbee_placed.actual_placement`). Not corrected; since mBee has no mounting error, the report writes base-relative poses as F_ee (any version) and tracker-relative poses as F_{trk,mBee}.
16. Figure 1: F_ce (arrow from the wrist ball to the tool plate) is not defined in the text. By position it is F_w F_we; by the subscript reading ({c} → {e}) it is F_cw F_w F_we. Figure 1's F_c arrow (base → wrist ball) actually spans F_c F_cw. The figure is schematic; use the p3 equations.
17. p3–5 minor (no effect on the math): p3 "F_c(θ1..3) = θ1 d1 + θ2 d2 + θ3 d3" equates a frame with a vector (read as Frame(I, Σ θ_k d_k)); p3 "The range of motion is as follows" is followed by blank space (the limits are listed above it); p4 "win which" → "in which"; p5 δ^rob_sys (k = 1..3 row) is missing k; p5 "DetachCalibrationMerker" → DetachCalibrationMarker; p5 "it's position" → its position.
18. p6 hint 1(d): "knowing the actual values of θ_k and φ_k will enable you to compute θ*_k and F_ee" → knowing the θ_k → θ*_k map (Δθ_k,sys) and φ_k lets you compute θ*_k and F*_ee. θ_k is always known (encoder value from State()); what is unknown is Δθ_k,sys and φ_k.
19. p5–6 minor (no effect on the math): "In particular, if …" is an unfinished sentence; ‖ε‖_FwdK → ‖ε_FwdK‖; α_iInvK → α_InvK; ε_Invk → ε_InvK; "This will can depend" → can depend; ω_k,sys in hint 1(a) is ω^rob_k,sys; stray "." after 1(e).

## 3.3 Report notation (updated while writing)
Source: `report/sections/02_variables.tex` (notation only; derivations stay in LaTeX).
- Marks: unmarked = nominal; * = actual (hidden); leading subscript `obs` = tracker output, `est` = our calibration result; stage labels `bl` (baseline), `init` (initial value), `est` (final). Index j = calibration sample (one move + one reading), k = joint or marker.
- Frames: workspace, {trk}, {rob} (base), {c} (after the linear stages), {w} (wrist center), {e} (end-effector). F_{x,y} = pose of y relative to x. Single-subscript poses keep the handout meaning (F_tracker, F_rob, F_mB relative to the workspace; F_m relative to the tracker).
- mBee coincides with {e}: base-relative poses are written F_ee in every version; the subscript mBee is used only relative to the tracker. Handout F_mBee (p5) = F_ee. Tool-mounting error ΔF_ee(η_ee) (p3) is written ΔF_we, with α_we, ε_we.
- Measurements: b_{obs,k,j} (`obs["mBee"].markers[k]`), F_{obs,trk,mBee,j} (`data.frames[j]`); actual b*_{k,j}, F*_{trk,mBee}(θ_j) (validation only).
- Base relative to the tracker: F*_{trk,rob} = F_tracker⁻¹ F*_rob (validation only); F_{bl,trk,rob} (`F_X_baseline`); F_{init,trk,rob,j} (local to `estimate_base_frame`); F_{init,trk,rob} (`F_X_nom` = `improved.F_X_init`); F_{est,trk,rob} (`improved.base_frame()`).
- Calibrated model: φ_{est,k}, Δθ_{est,k,sys}(θ_k), ΔF_{est,we} (`improved.params`, `parameters_report()`); F_{est,ee}(θ) = ImprovedFwdKins (`improved.fwd_kins`).
- Accuracy: ΔF_FwdK = (F*_ee)⁻¹ F_{est,ee}; ΔF_InvK between target and reached pose; both via `metrics.frame_error`.
- Code-only state: θ = `rob.theta_cmd` (encoder = command), θ* = `rob._theta_star`, θ_home = return of `home_robot()` (handout θ_encoders), t_elap = `clock.elapsed`.
- Shorthand (defined in 02 Conventions, used in 03): Δθ_k(θ_k) = Δθ^rob_{k,sys}; δ_k, ω_k = δ^rob_{k,sys}, ω^rob_{k,sys} (superscript rob vs trk separates robot and tracker errors); R_k = R(d_k, θ_k), k ≥ 4, R_w = R_4R_5R_6; p_cw = [500,0,0]ᵀ, p_we = [100,0,0]ᵀ. Base fit: F*_{trk,rob} = F_{init,trk,rob} ΔF_{trk,rob} with α_{trk,rob}, ε_{trk,rob} (`params[0:6]`; the code calls the base frame `F_X`).
- Error-model terms: δp_c (stage translation error); β_k (body rotation error of wrist joint k); γ = T_4β_4 + T_5β_5 + β_6 with T_4 = R_6ᵀR_5ᵀ, T_5 = R_6ᵀ (wrist rotation error); α_ee, ε_ee (body error of F_ee); r_j = [α_j; ε_j] (residual of sample j, `residuals`); J_j, J (residual Jacobian, `jacobian_rank_report`); ΔF_obs,j with α_obs,j, ε_obs,j (registration error).
- Parameters: x (parameter vector, `params`); t_{k,1}, t_{k,2} (tilt components on basis u_{k,1}, u_{k,2} ⊥ d_k); knots τ_{k,i}, spacing h_k, knot values c_{k,i} = Δθ_k(τ_{k,i}), hat weights w_{k,i}; c_{k,home} = −mean θ_home,k (`joint_offsets`); N_h (number of homings); gauge families G1–G5.
- Error propagation: e_k (interpolation error of joint k); N, ã_k, r, M (mBee marker count, centered positions, radius, rotation information matrix); L_j (readings averaged at sample j); G = ∇ε^trk_sys, w (skew part of G), α_trk (tracker rotation bias); C_reg, C_j, W (covariances and weights); Σ_rnd = diag(σ²_{k,rnd}); J_θ,j (distortion columns).
- Time and IK: T_k(Δ) (single-joint trapezoidal move time, `motion_time`); n_read; g(θ) (IK pose error); J_0, J_est (nominal and calibrated body Jacobian in θ); q (contraction factor).

## 3.4 Clarifications and interim conclusions
Non-obvious conclusions reached while working, each with its basis (handout page, or file:line under `assignments/assignment2/`). Inferences are left to the derivations. Notation as in 3.3.

### Phase 1 (line-by-line reading)
**A. Robot commands and the simulator**
1. **Encoder vs physical joint.** p3: θ*_k = θ_k + Δθ_k,rnd + Δθ_k,sys, State() returns θ_k; `src/simulation/robot.py:92-93`: `theta_cmd = theta`, `_theta_star = theta + _delta_theta_sys(theta) + rnd`. → The reported θ equals the last command exactly; all joint error lies between θ and θ*; Δθ_sys is evaluated at the encoder value.
2. **No motion dynamics.** `robot.py:91-94` advances the clock by the whole motion time, then sets the final θ and θ* in one step. → No intermediate state; the tracker cannot observe the robot during a move.
3. **Motion time.** p4: t_settle + slowest joint; `src/robot.py` `motion_time` uses a trapezoidal profile and `T_SETTLE = 0.05 s` (neither in the handout); wrist speed 0.1 rad/s (p5). → A π/2 wrist move takes ≈ 16 s. Docstring `robot.py:86`: a move to the current pose still costs t_settle and draws a new Δθ_rnd.
4. **Homing.** p4: HomeRobot places the robot at θ*_k = 0 and returns the encoder values; `robot.py:57-63` iterates θ ← −Δθ_sys(θ) − Δθ_rnd (new Δθ_rnd per call); `robot.py:112` sets θ* = 0. → Return ≈ −Δθ_sys(0) − Δθ_rnd; repeated homings scatter about −Δθ_sys(0) with std σ_rnd. `robot.py:46-47` does the same at creation without advancing the clock, so the first State() is generally not zero.
5. **Commands in pose space.** p4: MoveRobot(F) = MoveJoints(InvKins(F)), CommandedPose = FwdKins(θ); `src/robot.py` `commanded_pose` returns `fwd_kins(theta_cmd)`; notebook Step 10: `theta = kins.inv_kins(...)` then `rob.move_joints(theta)`. → The robot stores only θ; CommandedPose is a nominal prediction and never shows an error; a calibrated pose is commanded by passing ImprovedInvKins(F) to MoveJoints.
6. **When mBee moves.** `_sync_calibration_body` is called at `robot.py:94` (move), `robot.py:113` (homing), `calibration_body.py:53` (attach) and only updates an attached body; detach sets `visible = False` (`calibration_body.py:62`); `calibration_body.py:42` attaches at creation. → The body starts attached and follows the robot; a detached body keeps its last pose and is not seen.

**B. Kinematic structure and errors**
1. **F_cw always acts along the base x axis.** p3: F_c = θ1 d1 + θ2 d2 + θ3 d3 (a translation), no error listed for F_cw; actual model `robot.py:68,72`: `Frame(Rot(), p_c) * F_CW * ...` with tilted axes only inside `p_c`. → Tilts change the direction of travel, not the orientation of {c}; F_c F_cw = Frame(I, p_c + [500,0,0]ᵀ) in both models; the wrist-center position depends only on θ1..3.
2. **Wrist axes.** p3: F_w is a product of rotations; `robot.py:69-71`: actual wrist from `exp_so3` rotations without translation, order 4, 5, 6. → Tilted wrist axes still meet at the wrist center (no axis offsets in the model); n5, n6 are expressed in the frames after the preceding wrist rotations.
3. **Two parameters per tilted axis.** `create_robot` draws φ_k ⊥ d_k (`sample_perpendicular`); `src/student/kinematics.py:33`: "two components each in the plane perpendicular to the nominal axis". A rotation about d_k leaves d_k unchanged. → Five tilted axes carry ten parameters.
4. **Form of Δθ_sys.** p3 gives only the bounds δ^rob_k,sys and ω^rob_k,sys; the simulator uses c + sθ + σ sin(Aθ + B) (`robot.py:51-55`), σ = σ_k,sys (p5 table). → This form is hidden ground truth and must not be assumed; only the two bounds may be used.
5. **Errors depend on the seed.** `create_robot` and `create_tracker` draw every static error from `seed` with norm in [0.5, 1] × bound (`BOUND_MIN_FRAC`); notebook Step 2: grading uses other seeds. → Rely only on the handout's bounds, not on values seen for one seed.

**C. Tracker and measurements**
1. **Base relative to the tracker is one constant unknown.** p3: σ_Ta = σ_Tp = 0, so F*_tracker = F_tracker (user-specified). → F*_{trk,rob} = F_tracker⁻¹ F*_rob contains only the unknown ΔF_rob and is constant; estimating it is equivalent to estimating F*_rob.
2. **Who performs the SVD registration.** p2: SampleMarkerBodies computes and returns the frames; `src/simulation/tracker.py:102` delegates to the A1 sampler, which uses the simulator's `procrustes_solver`; `src/student/registration.py:18`: `register_points` must be "your own -- do not call the simulator's solver" (repeated in notebook Step 5). → Frames from SampleMarkerBodies may be used as tracker outputs; any additional registration in student code (e.g. `refine_marker_body`) must use the student's own `register_points`.
3. **Error content of an mBee observation.** p5: mBee's a*_k are actual and its frame corresponds exactly to F_ee; `calibration_body.py:37-38` sets zero manufacturing error; each marker reading subtracts `systematic_error(p)` and adds Gaussian noise (A1 `tracker.py:110-112`, called by the A2 sampler). → mBee adds no geometry error of its own; every reading carries ε_b (new per reading) and ε^trk_sys (drawn once per tracker in `create_tracker`).
4. **Visibility.** `src/simulation/tracker.py` `sample_marker_bodies` returns None for a body with any marker outside `trk.is_visible` (clock already advanced); volume = Figure 2 truncated pyramid, 1000–2200 mm deep, half-width 500–1000 mm (`Tracker.FRUSTUM_*`). → Every calibration pose must keep all mBee markers inside the volume, or the sample is lost while its time is still charged.
5. **Two time budgets.** p1, p6: short calibration and testing time, measured by t_elap (`clock.elapsed`); p7: program execution ≤ 10 min; no code measures wall-clock time. → t_elap counts only moves and samples; the 10 min limit counts all computation; the two are independent.

**D. Calibration pipeline in the provided code**
1. **Base estimate before the fit.** `src/student/workflow.py:107-121`: every sample satisfies F_ee,j = F_X · kins.fwd_kins(θ_j) for one constant unknown F_X; "Estimate F_X from all samples (your average_frames may help)"; `kins` is "the nominal Robot at first". Notebook Steps 6–7: `F_X_baseline = estimate_base_frame(baseline, rob)` (≈ 10 poses), `F_X_nom = estimate_base_frame(data, rob)` (full data), `F_X_nom` passed as `F_X_init`. → Both estimate F*_{trk,rob} with the nominal kinematics; `F_X_baseline` only reports the nominal model's mismatch; `F_X_nom` is the starting value of the fit.
2. **The fit works in the tracker frame.** `kinematics.py:156-157`: `residuals` compares `predict_in_tracker(theta_j, params)` with `data.frames[j]`; `kinematics.py:91-92`: `predict_in_tracker = base_frame(params) * fwd_kins(theta, params)`; `kinematics.py:32` (example layout): base twist in `params[0:6]`. → Base and kinematic parameters are adjusted together in one least-squares problem; each observation is compared with F_{est,trk,rob} F_{est,ee}(θ_j) without converting it to the base frame.
3. **Evaluation.** Notebook Step 9: ΔF_i = (F_trk⁻¹ F*_ee(θ_i))⁻¹ (F̂_X · ImprovedFwdKins(θ_i)); Step 10 moves the robot with the computed θ and compares the target with `mbee_placed.actual_placement`. → The forward error is measured in the tracker frame and includes the base estimate; the inverse error is measured on the pose actually reached, including Δθ_rnd.
4. **Comparing parameters with ground truth.** `parameters_report` docstring (`kinematics.py`): some parameters "are only defined up to the base-frame gauge (and so are better compared as angles between axes)". → Compare angles between axes rather than single axis directions.
