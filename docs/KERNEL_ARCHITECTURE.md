# K.E.R.N.E.L. Architecture

## Knowledge-Enhanced Robust Neural Evaluation Layer

### Vision

Transform WALLS from a simple binary classifier into a **multi-modal, continuous-output mental health assessment system** that:

1. Captures nuance through Likert scales and continuous inputs
2. Understands free-text through modern sentence embeddings
3. Produces smooth, probabilistic outputs with confidence intervals
4. Supports temporal modeling and reinforcement learning
5. Provides clinically meaningful, interpretable results

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND INPUT LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   LIKERT    │  │   SLIDERS   │  │  FREE TEXT  │  │  OPTIONAL   │        │
│  │   SCALES    │  │   (0-100)   │  │ + SENTIMENT │  │   EXTRAS    │        │
│  │   (1-5)     │  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                    │                                         │
│                           Unified Input Vector                               │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING & ENCODING LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────┐    ┌───────────────────────────┐            │
│  │    TABULAR ENCODER        │    │    TEXT ENCODER           │            │
│  │                           │    │                           │            │
│  │  • Likert → normalized    │    │  • Sentence Transformer   │            │
│  │  • Sliders → [0,1]        │    │    (all-MiniLM-L6-v2)     │            │
│  │  • Categorical → embed    │    │  • Sentiment scores       │            │
│  │  • Missing → learned      │    │  • Keyword extraction     │            │
│  │                           │    │  • 384-dim embedding      │            │
│  └─────────────┬─────────────┘    └─────────────┬─────────────┘            │
│                │                                │                           │
│                └──────────────┬─────────────────┘                           │
│                               │                                              │
│                   Concatenated Feature Vector                                │
│                   [tabular_dim + 384 + sentiment_3]                          │
│                                                                              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NEURAL PREDICTION LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Multi-Task Neural Network                         │    │
│  │                                                                      │    │
│  │    Input (N features)                                                │    │
│  │         │                                                            │    │
│  │         ▼                                                            │    │
│  │    ┌─────────────────┐                                               │    │
│  │    │  Shared Trunk   │  Dense(256) → ReLU → Dropout(0.2)             │    │
│  │    │                 │  Dense(128) → ReLU → Dropout(0.2)             │    │
│  │    │                 │  Dense(64)  → ReLU → Dropout(0.1)             │    │
│  │    └────────┬────────┘                                               │    │
│  │             │                                                        │    │
│  │    ┌────────┴────────┬───────────────┬───────────────┐               │    │
│  │    ▼                 ▼               ▼               ▼               │    │
│  │ ┌──────┐         ┌──────┐       ┌──────┐       ┌──────┐              │    │
│  │ │Stress│         │Depr. │       │Anxi. │       │Sleep │              │    │
│  │ │ Head │         │ Head │       │ Head │       │ Head │              │    │
│  │ └──┬───┘         └──┬───┘       └──┬───┘       └──┬───┘              │    │
│  │    │                │               │               │                │    │
│  │    ▼                ▼               ▼               ▼                │    │
│  │  Mean+Var        Mean+Var       Mean+Var       Mean+Var              │    │
│  │ (0-100)         (0-27 PHQ)     (0-21 GAD)      (0-10)                │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Output: {                                                                   │
│    "stress": {"mean": 45.2, "std": 8.3, "ci_lower": 38.9, "ci_upper": 51.5}, │
│    "depression": {"mean": 12.4, "std": 3.1, ...},                            │
│    "anxiety": {"mean": 8.7, "std": 2.2, ...},                                │
│    "sleep": {"mean": 6.8, "std": 1.5, ...}                                   │
│  }                                                                           │
│                                                                              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VISUALIZATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     3D AI VISUALIZATION ZONE                        │     │
│  │                                                                     │     │
│  │  • Neural Network Live Graph (animated node activations)            │     │
│  │  • 3D Mental State Manifold (t-SNE/UMAP embedding space)            │     │
│  │  • Confidence Ribbon Charts (uncertainty visualization)             │     │
│  │  • Pulsing Neuron Clusters (real-time inference display)            │     │
│  │  • Embedding Space Navigator (explore similar states)               │     │
│  │                                                                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     2D CLINICAL CHARTS                              │     │
│  │                                                                     │     │
│  │  • Radar with confidence bands                                      │     │
│  │  • Time series with moving average + variance bands                 │     │
│  │  • Likert response heatmap                                          │     │
│  │  • PHQ-9/GAD-7 validated score displays                             │     │
│  │                                                                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Improvements

### 1. Input Layer Redesign

**Before**: 24 binary yes/no questions
**After**: Multi-modal input system

| Input Type | Range | Purpose |
|------------|-------|---------|
| Likert Scale | 1-5 | Validated PHQ-9, GAD-7 items |
| Continuous Slider | 0-100 | Subjective intensity measures |
| Free Text | String | Sentiment + semantic embedding |
| Categorical | Enum | Demographics, lifestyle factors |
| Optional Extras | Various | Context-dependent questions |

### 2. Text Processing Upgrade

**Before**: TF-IDF (bag-of-words, loses context)
**After**: Sentence Transformers + VADER sentiment

- **Sentence embedding**: 384-dimensional dense vector capturing meaning
- **Sentiment scores**: Positive, negative, neutral, compound
- **Keyword extraction**: Clinical terms for interpretability

### 3. Model Output Redesign

**Before**: Single point predictions with hard classifications
**After**: Distributional outputs with uncertainty

```python
# Old output
{"stress_score": 45.2}

# New output
{
    "stress": {
        "mean": 45.2,
        "std": 8.3,
        "ci_lower": 38.9,      # 95% CI
        "ci_upper": 51.5,
        "percentile": 72,       # Where this falls in population
        "trend": "stable",      # vs previous
        "clinical_band": "moderate"
    }
}
```

### 4. Statistical Smoothing

**Problems with current system:**
- Outputs jump dramatically with small input changes
- No uncertainty quantification
- Binary classifications are too harsh

**Solutions:**
- Monte Carlo dropout for uncertainty estimation
- Exponential moving average across sessions
- Ensemble of 3 models with variance estimation
- Calibrated probability outputs

---

## Clinical Validity

### Validated Instruments Incorporated

1. **PHQ-9** (Patient Health Questionnaire-9)
   - 9 items, 0-3 Likert scale
   - Total score 0-27
   - Validated cutoffs: 5, 10, 15, 20

2. **GAD-7** (Generalized Anxiety Disorder-7)
   - 7 items, 0-3 Likert scale
   - Total score 0-21
   - Validated cutoffs: 5, 10, 15

3. **PSS-10** (Perceived Stress Scale)
   - 10 items, 0-4 Likert scale
   - Total score 0-40

4. **PSQI** (Pittsburgh Sleep Quality Index)
   - Sleep quality components
   - Score 0-21

---

## RL-Ready Structure

Each user interaction is stored in a format suitable for future reinforcement learning:

```json
{
    "state": {
        "features": [...],
        "embedding": [...],
        "previous_scores": {...}
    },
    "action": {
        "questions_shown": [...],
        "question_order": [...],
        "ui_variant": "A"
    },
    "reward": {
        "engagement": 0.8,
        "completion": true,
        "user_feedback": null,
        "clinical_validation": null
    },
    "next_state": {
        "scores": {...},
        "confidence": {...}
    }
}
```

This enables:
- Adaptive question ordering
- Personalized UI optimization
- Clinical outcome optimization

