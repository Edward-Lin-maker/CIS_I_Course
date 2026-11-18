# Report guidance distilled from the A1 rubric

## Status and limits
Source: four photographed A1 rubric pages (`rubric1.jpg` to `rubric4.jpg`), read together with the A3 handout, pp. 1-3 and 7-8. The photos are cropped and some details are incomplete. This is a transferable writing checklist, not an official A3 grading rubric. Do not carry A1 scores, variable names, robot calibration tasks, or marker counts into A3.

## Transferable criteria
1. **Problem and specifications.** Make the goal understandable without the handout. State measurable requirements, units, ergonomics and evaluation definitions; distinguish handout requirements from implementation choices.
2. **Design and rationale.** Use a dimensioned sketch showing marker bodies, markers, tip and relevant frames. Quantitative tables must agree with sketches and code. Explain why dimensions, positions and sampling choices were selected.
3. **Mathematics.** Define frames/variables and derive the implemented equations, including observations, residuals and uncertainty when used. Cite original lecture/material sources near the equations; mark original derivations as such. Identify degenerate geometry, corner cases and valid assumptions.
4. **Algorithms.** Connect mathematics to the actual notebook and assignment-specific functions. Give inputs, outputs, steps, stopping/failure conditions and meaningful constants. Include a workflow diagram or explicit call tree. Do not document trivial library operations or copy code line by line.
5. **Validation.** Identify each major component, independent test-data construction, expected answer, test procedure and outcome. Include end-to-end and corner-case tests, sensitivity where useful, and explain failures. Compare achieved values with exact requirements and disclose limitations.
6. **Consistency and reproducibility.** The notebook must run from the documented clean environment. Report numbers and figures must match identifiable saved outputs, seeds and settings. Distinguish archived results from reruns and simulated time from actual runtime.
7. **Attribution.** State AI/tool use, the assistance requested and relevant prompts, external code sources and team contributions. The A3 handout is the authority for its disclosure requirements. Keep an assistance record while working; no invented claims of non-use.

## A1-specific criteria that are not carried over
- A1 F_ptr/F_cal formulas, sensed-point covariance, hand-guided robot positions and calibration-specific corner cases do not become A3 tasks by analogy.
- The A1 point allocations are not an A3 scoring scheme. One visible algorithm subtotal does not match the displayed item sum; do not reconstruct scores from these photos.
- Sketches are judged for communicating the actual proposed design, not merely for existing. Use the A3 pointer/reference-body scenario rather than an A1 device drawing.

## A3-specific completion checks
- Include selected patch IDs and sample counts, accepted/rejected sample lists, and residual mean/std/max/p90.
- Distinguish sample residuals (FRE-related) from TRE on mesh vertices; report uncertainty/predicted TRE if implemented, following the starter output interface.
- Explain outlier rejection, registration initialization, convergence and failure behavior.
- Document actual runtime <= 10 minutes and a realistic simulated acquisition time.
- Retain separate handout and README requirements where they disagree; see `course_reference.md` Part 4.4.

## Before submission
Check the signed cover, team contributions, AI prompts/credits, equation citations, report/notebook agreement, all required result fields, included input data, documented clean installation, and a successful end-to-end run. Empty template sections are not evidence that these checks have been completed.
