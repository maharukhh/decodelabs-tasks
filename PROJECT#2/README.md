# Project 2 — Automated Quality Inspection (Computer Vision)
### DecodeLabs Robotics & Automation Internship — Industrial Training Kit

## 🎯 Goal
Build a computer-vision pipeline that looks at a gear on a conveyor belt
and decides **PASS** or **FAIL** — flagging broken teeth or cracks — using
OpenCV, with zero manual review.

## 📁 Folder contents

```
project2/
├── README.md                  ← this file
├── requirements.txt
├── generate_test_images.py    ← builds a 10-image synthetic test dataset
├── gear_inspection.py         ← the actual IPO inspection pipeline
├── test_images/               ← 5 perfect + 5 defective gear images (generated)
└── output/                    ← annotated PASS/FAIL images (generated after running)
```

> **Why synthetic images?** DecodeLabs didn't ship a real camera dataset
> with the brief, so `generate_test_images.py` draws 10 gear images with
> OpenCV (5 perfect, 5 with a broken tooth / crack + realistic sensor
> noise) — enough to prove the pipeline actually works end-to-end. Swap in
> your own factory photos any time by dropping them into `test_images/`.

## 🧠 The pipeline (matches the slide deck's IPO architecture)

### Phase 1 — Isolating the Signal from the Noise
```python
gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred  = cv2.GaussianBlur(gray, (5, 5), 0)
_, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
```
Flattens the image to grayscale, smooths sensor noise, then binarizes so
the gear becomes a clean white silhouette on a black background.

### Phase 2 — Topological Analysis
```python
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
hull        = cv2.convexHull(contour, returnPoints=False)
defects     = cv2.convexityDefects(contour, hull)
```
1. **Find the boundary** — trace the gear's outer silhouette.
2. **Rubber band (convex hull)** — the smallest convex shape wrapping the gear.
3. **Measure the gaps (convexity defects)** — every dip between the hull
   and the real contour is a "defect" candidate — normal tooth gaps *and*
   real breaks both show up here, which is why calibration matters (next).

### Phase 3 — The Tolerance Gate
```python
actual_distance = d_raw / 256.0          # OpenCV's fixed-point trap
if actual_distance > DEFECT_DISTANCE_THRESHOLD_PX:
    # real structural defect -> FAIL
```
Every gear has *normal* tooth-gap defects (~25–26 px deep in this
dataset). A **broken tooth** collapses much deeper (~34–104 px). The
threshold (`DEFECT_DISTANCE_THRESHOLD_PX = 30.0`) is calibrated to sit
between those two ranges — this is the exact "tolerance gate" concept
from the slides, and it's the number you'd re-calibrate per real part
geometry and lighting setup.

### Output
- Draws a red bounding box + marks each real defect point
- Prints `PASS` / `FAIL: STRUCTURAL DEFECT DETECTED` on the image
- Saves the annotated image to `output/`
- Prints a simulated binary `FAIL_BIT` signal, as if sent to a PLC

## ▶️ How to run

```bash
pip install opencv-python numpy --break-system-packages

# 1. Generate the test dataset (5 OK + 5 DEFECT gear images)
python3 generate_test_images.py

# 2. Run the inspection pipeline against all of them
python3 gear_inspection.py
```

Expected output: a per-image PASS/FAIL verdict, defect coordinates +
depth for anything flagged, and a final sorting-accuracy score. On the
bundled dataset this pipeline hits **100% (10/10)** sorting accuracy.

## 🔧 Calibrating for real hardware
If you swap in real camera images:
1. Check `THRESHOLD_VALUE` — real parts may need adaptive thresholding
   (`cv2.adaptiveThreshold`) if lighting isn't uniform.
2. Re-measure normal tooth-gap depth on a few known-good parts, then set
   `DEFECT_DISTANCE_THRESHOLD_PX` just above that ceiling.
3. If parts are reflective metal, consider a bilateral filter instead of
   Gaussian blur (see the "Why Gaussian?" slide comparison) to preserve
   sharp edges.

## 📝 What to submit
1. `gear_inspection.py` + `generate_test_images.py`
2. A couple of `output/result_*.jpg` screenshots (one PASS, one FAIL)
3. Your final sorting-accuracy number and a short note on how you picked
   `DEFECT_DISTANCE_THRESHOLD_PX`
