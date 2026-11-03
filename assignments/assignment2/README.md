# CIS I Assignment 2 - code submission

Completed calibration code for a Cartesian robot (three stage and three wrist
joints). Keep this folder inside the full course repository: it imports the
provided Assignment 1 tracker and the root data_types/uncertainty modules.
The written report is submitted separately.

## Run

Use Python 3.9 or newer (validated on an Apple Silicon Mac with Python 3.12).
From assignments/assignment2:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests -q
jupyter notebook notebooks/assignment2_template.ipynb
```

Choose this environment as the notebook kernel and run all cells in order.
The notebook expects notebooks/ as its working directory, as in the course
template. It includes the 81-case test suite, scene/visibility checks,
homing, calibration, fixed-grid forward/inverse tests, multiple seeds and
full-range base-frame evaluation. The simulator and nominal robot are unchanged.

## Files

- src/student/: metrics, point registration/frame averaging, workflow and fitted kinematics.
- tests/test_student.py: the original 23 student cases.
- tests/test_kinematics_validation.py: 35 independent and edge-case checks.
- tests/test_simulation.py: 23 unchanged course cases.
- tests/kinematics_sensitivity.py: optional controlled experiment driver.
- tests/data/: shipped per-run and aggregate controlled-experiment CSV data.
- notebooks/assignment2_template.ipynb: the complete workflow and saved outputs.

The controlled plot is drawn from the shipped CSV data, without report files.
To regenerate the controlled data and a PNG in tests/data/:

```bash
python tests/kinematics_sensitivity.py
```

The notebook defaults to loading the saved data; set RECOMPUTE_SENSITIVITY=True
only to rerun those additional experiments. Consecutive repeated commands are
retained as allowed by the course template.

## Accuracy and timing

Tracker-frame forward and inverse errors meet the targets in the evaluated
seed sets. Accuracy relative to the hidden actual robot base does not meet
both targets for every seed; the notebook reports these errors and failed
inverse solves explicitly. Ground truth is used only for tests, evaluation
and parameter reporting, never for calibration.

A fresh full notebook run on the validation Mac took 123.24 seconds,
including the tests and extended evaluations. Simulated motion/sampling time
is reported separately and must not be interpreted as execution time.
