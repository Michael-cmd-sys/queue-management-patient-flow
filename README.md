# Queue Management via Surveillance Camera for Patient Flow
### Applied Mathematics Senior Thesis Project

[![Institution: KNUST](https://img.shields.io/badge/Institution-KNUST%20Dept.%20of%20Mathematics-green.svg)](https://www.knust.edu.gh/)
[![Field: Applied Mathematics](https://img.shields.io/badge/Field-Applied%20Mathematics%20%26%20Computer%20Vision-blue.svg)]()
[![Python: 3.13+](https://img.shields.io/badge/Python-3.13%2B-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## 🎓 Academic Metadata

* **Thesis Title**: *Queue Management via Surveillance Camera for Patient Flow*
* **Department**: Department of Mathematics, Faculty of Physical Sciences
* **Institution**: Kwame Nkrumah University of Science and Technology (KNUST), Kumasi, Ghana
* **Authors**: Nurudeen Hamzah, Amoah Jeffery Jojo, Michael Awumi
* **Supervisor**: Prof. Yirenkyi
* **Date**: February 2026

---

## 📌 Abstract & Research Problem

In many Low- and Middle-Income Countries (LMICs), hospital queue management relies heavily on manual First-Come-First-Served (FCFS) processes. This manual paradigm suffers from operational blindness, high variance in patient waiting times, queue jumping, and inefficient resource allocation.

This senior thesis formulates a **mathematical and computer-vision-based framework** to transform passive CCTV surveillance infrastructure into an automated, real-time queue monitoring and Expected Wait Time (EWT) prediction engine. The system integrates deep spatial object detection (YOLOv8), multi-object temporal trajectory tracking (ByteTrack), computational geometry (Point-in-Polygon ray-casting), and queueing theory.

---

## 🧮 Mathematical Formulation & Theoretical Framework

### 1. Spatial Geometry & Point-in-Polygon Membership
Let $\Omega_{\text{ROI}} \subset \mathbb{R}^2$ be a closed, planar non-self-intersecting polygon defining the spatial queue region of interest. For a bounding box $B_i = (x_1, y_1, x_2, y_2) \in \mathbb{R}^4$ representing a detected individual, we extract their ground contact point (feet level):

$$P_i = \left( \frac{x_1 + x_2}{2}, y_2 \right) \in \mathbb{R}^2$$

The queue membership indicator function $\mathbb{I}_{\text{Queue}}(P_i)$ is evaluated using the Ray-Casting algorithm (derived from the Jordan Curve Theorem):

$$\mathbb{I}_{\text{Queue}}(P_i) = \begin{cases} 1 & \text{if } P_i \in \Omega_{\text{ROI}} \\ 0 & \text{if } P_i \notin \Omega_{\text{ROI}} \end{cases}$$

### 2. Instantaneous Queue Length & Trajectory Dynamics
At discrete timestamp $t$, given $K(t)$ active temporal tracks $\mathcal{T}(t) = \{\tau_1, \tau_2, \dots, \tau_K\}$, the instantaneous queue length $N(t)$ is defined as:

$$N(t) = \sum_{i=1}^{K(t)} \mathbb{I}_{\text{Queue}}(P_i(t))$$

For each tracked patient $i$, the total observed queue dwell duration $T_{\text{dwell}, i}$ between entry time $t_{\text{entry}, i}$ and exit time $t_{\text{exit}, i}$ is:

$$T_{\text{dwell}, i} = \int_{t_{\text{entry}, i}}^{t_{\text{exit}, i}} \mathbb{I}_{\text{Queue}}(P_i(\tau)) \, d\tau$$

### 3. Expected Wait Time (EWT) Model
Based on queueing theory fundamentals (Little's Law under a deterministic or Markovian service rate $\mu$):

$$\text{EWT}(t) = \frac{N(t)}{\mu}$$

where:
* $N(t)$ = Instantaneous count of patients inside $\Omega_{\text{ROI}}$ at time $t$.
* $\mu$ = Mean service rate (patients served per unit time by triage/consultation staff).

---

## 📊 Empirical Evaluation Metrics

To rigorously benchmark the automated system against ground-truth manual video observations, we formulate three statistical evaluation dimensions:

### Dimension 1: Spatial Queue Count Accuracy (MAPE)
Evaluated across $M$ temporal evaluation windows (e.g. 5-minute sampling intervals):

$$\text{MAPE} = \frac{100\%}{M} \sum_{m=1}^{M} \left| \frac{N_{\text{actual}}(t_m) - N_{\text{pred}}(t_m)}{N_{\text{actual}}(t_m)} \right|$$

> **Note:** Windows where $N_{\text{actual}}(t_m) = 0$ are excluded from the MAPE computation (the denominator is undefined for zero ground-truth counts). Only non-zero windows contribute to the summation.

### Dimension 2: Waiting Time Prediction Error (MAE & RMSE)
Comparing actual duration spent in queue $T_{\text{actual}, k}$ vs. predicted wait time $\text{EWT}_k$ across a sample size of $K$ patients:

$$\text{MAE} = \frac{1}{K} \sum_{k=1}^{K} |T_{\text{actual}, k} - \text{EWT}_k|$$

$$\text{RMSE} = \sqrt{ \frac{1}{K} \sum_{k=1}^{K} \left( T_{\text{actual}, k} - \text{EWT}_k \right)^2 }$$

### Dimension 3: Perceptual Detection Performance ($F_1$-Score)
$$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall} + \epsilon}$$

---

## 📁 Repository Architecture & Functional Pipeline

This project adheres strictly to **Functional Programming (FP)** principles: pure side-effect-free math functions, immutable dataclasses (`frozen=True`), typed config schemas, and decoupled I/O adapters.

```
queue-management-patient-flow/
├── .agents/skills/cv-functional-mlops/  # Custom Functional MLOps skill
├── docs/
│   └── presentation.pdf                 # KNUST Thesis Defense Presentation (25 slides)
├── models/
│   └── best.pt                          # Custom fine-tuned YOLOv8 model weights
├── data/
│   ├── input_videos/                    # Raw patient queue video clips
│   └── output/                          # Generated metrics JSON and annotated video
├── src/
│   ├── schema.py                        # Immutable domain contracts (Point, BoundingBox, QueueSnapshot)
│   ├── config.py                        # Immutable hyperparameter & path configurations
│   ├── vision/
│   │   ├── detector.py                  # YOLOv8 object detection wrapper
│   │   └── tracker.py                   # Modern ByteTrackTracker trajectory tracking
│   ├── analytics/
│   │   ├── spatial.py                   # Pure Ray-Casting Point-in-Polygon algorithm
│   │   └── queue_math.py                # Pure EWT math, MAE, RMSE, and MAPE metrics
│   ├── evaluation/
│   │   └── plot_metrics.py              # Time-series analytics visualization generator
│   └── pipeline.py                      # Pure pipeline orchestrator
├── tests/
│   └── test_analytics.py                # Pytest unit tests for spatial & mathematical routines
├── main.py                              # Entrypoint execution script
└── pyproject.toml                       # uv project setup
```

---

## 🚀 Quickstart & Pipeline Execution

### Prerequisites
* Python $\ge 3.13$
* [`uv`](https://github.com/astral-sh/uv) fast package manager
* `models/best.pt` — Custom fine-tuned YOLOv8 weights **not distributed via git** (see `.gitignore`). Download from the [release assets](https://github.com/Michael-cmd-sys/queue-management-patient-flow/releases) or train a custom model per the thesis data, then place at `models/best.pt` before running.

### 1. Installation & Environment Setup
```bash
git clone https://github.com/Michael-cmd-sys/queue-management-patient-flow.git
cd queue-management-patient-flow
uv sync
```

### 2. Run Analytics Pipeline
Execute the full detection, tracking, spatial ROI, and EWT calculation pipeline:
```bash
uv run python main.py
```

### 3. Run Mathematical Unit Tests
```bash
uv run pytest
```

### 4. Generate Time-Series Thesis Plots
```bash
uv run python src/evaluation/plot_metrics.py
```

---

## 📚 Primary Academic References

1. **Fosu, G. O., Akweittey, E., Opong, J. M., & Otoo, M. E. (2020)**. *Vehicular traffic models for speed-density-flow relationship*. Journal of Mathematical Modeling.
2. **Fosu, G. O., Oduro, F. T., & Caligaris, C. (2021)**. *Multilane analysis of a viscous second-order macroscopic traffic flow model*. SN Partial Differential Equations and Applications, 2(7), 1-17.
3. **Appati, J. K., Gogovi, G. K., & Fosu, G. O. (2015)**. *Matlab implementation of Vogel's approximation and the modified distribution methods*. Compusoft, 4(1), 1449.
4. **Taton, T. K., Saha, B., Akter, A., Islam, M. J., & Mostaque, S. K. (2024)**. *Waiting time prediction in queue management: leveraging machine learning approach*. IEEE ICRPSET, 1-5.
