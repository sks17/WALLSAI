# K.E.R.N.E.L. System Explanation

## Knowledge-Enhanced Robust Neural Evaluation Layer

This document explains the data science reasoning behind every improvement in the KERNEL system redesign.

---

## 1. Why We Moved Beyond Binary Yes/No Questions

### The Problem

Binary questions (yes/no) suffer from several statistical issues:

1. **Information Loss**: A yes/no answer compresses a continuous internal state into 1 bit of information
2. **Ceiling/Floor Effects**: People with extreme experiences cannot express intensity
3. **Social Desirability Bias**: Binary choices are more susceptible to "safe" answers
4. **Poor Discrimination**: Cannot distinguish between mild and severe cases

### The Solution: Multi-Modal Inputs

| Input Type | Information Content | Use Case |
|------------|---------------------|----------|
| Binary (yes/no) | 1 bit | Simple screening |
| Likert (0-3) | ~2 bits | Validated instruments (PHQ-9, GAD-7) |
| Slider (0-100) | ~7 bits | Subjective intensity |
| Free Text | Variable | Context, nuance, temporal information |

### Data Science Rationale

**Likert Scales** are used because:
- They map directly to validated clinical instruments (PHQ-9, GAD-7)
- The 0-3 scale has been psychometrically validated
- Enables direct comparison with clinical norms

**Sliders** provide:
- Continuous response that captures intensity gradients
- Better variance in the data for regression models
- More sensitive to treatment effects over time

**Free Text** captures:
- Temporal information ("for the past month...")
- Context ("because of my job loss...")
- Qualitative nuance not expressible in structured questions

---

## 2. Why We Replaced TF-IDF with Sentence Embeddings

### The Problem with TF-IDF

TF-IDF (Term Frequency-Inverse Document Frequency) has fundamental limitations:

1. **Bag-of-Words**: Ignores word order and context
   - "I don't feel sad" and "I feel sad" have similar TF-IDF vectors
   
2. **Vocabulary Mismatch**: Out-of-vocabulary words get zero weight
   - Typos, slang, and novel expressions are lost

3. **Dimensionality**: Creates sparse, high-dimensional vectors
   - Requires many more training samples

4. **No Semantic Understanding**: Cannot capture meaning
   - "depressed" and "down in the dumps" are unrelated in TF-IDF

### The Solution: Sentence Transformers + Sentiment

We now use a two-pronged approach:

#### Sentence Transformers (all-MiniLM-L6-v2)

- **Dense embeddings**: 384 dimensions instead of 10,000+ sparse features
- **Semantic similarity**: "I feel anxious" ≈ "I'm worried all the time"
- **Pre-trained**: Learned from millions of sentence pairs
- **Robust**: Handles typos, synonyms, paraphrasing

#### VADER Sentiment Analysis

- **Rule-based**: Designed specifically for social media/informal text
- **Handles negation**: "I don't feel good" → negative sentiment
- **Intensity**: "very sad" vs "sad" vs "a little sad"
- **Four scores**: positive, negative, neutral, compound

### Data Science Rationale

```
TF-IDF representation:
"I've been feeling really anxious lately" → [0, 0, 0.3, 0, 0.4, 0, ...]
                                            (sparse, 10000+ dims)

Sentence embedding:
"I've been feeling really anxious lately" → [0.12, -0.34, 0.56, ...]
                                            (dense, 384 dims)
```

The embedding space has the property that similar meanings cluster together:
- "feeling anxious" → close to "worried", "nervous", "on edge"
- Far from "happy", "content", "relaxed"

This allows the model to generalize from training examples to novel phrasings.

---

## 3. Why We Output Distributions Instead of Point Estimates

### The Problem with Point Estimates

A model that outputs `stress_score = 45.2` implies false precision:
- No indication of model uncertainty
- No way to know if the model is confident or guessing
- Encourages over-interpretation of small differences

### The Solution: Distributional Outputs

Each prediction now includes:
- **Mean (μ)**: The central estimate
- **Standard Deviation (σ)**: Model uncertainty
- **95% Confidence Interval**: [μ - 1.96σ, μ + 1.96σ]

### How It Works

#### Method 1: Direct Variance Prediction

The neural network has two output neurons per target:
1. Mean prediction (μ)
2. Log-variance prediction (log σ²)

The loss function combines:
- **Prediction error**: How far the mean is from the true value
- **Calibration error**: Whether the variance matches actual error distribution

```python
# Gaussian negative log-likelihood loss
loss = (y_true - μ)² / (2σ²) + log(σ²) / 2
```

This incentivizes the model to:
- Predict accurate means
- Output larger σ when uncertain
- Output smaller σ when confident

#### Method 2: Monte Carlo Dropout

At inference time, we run the model multiple times with dropout enabled:

```python
predictions = []
for _ in range(10):
    pred = model(input, training=True)  # Dropout active
    predictions.append(pred)

mean = np.mean(predictions)
std = np.std(predictions)
```

This samples from the posterior distribution of weights, providing:
- Epistemic uncertainty (what the model doesn't know)
- Better calibrated confidence intervals

### Data Science Rationale

**Calibration**: A well-calibrated model should have its 95% CI contain the true value 95% of the time. This is testable and improvable.

**Clinical Decision Making**: Knowing that "depression = 12 ± 2" is very different from "depression = 12 ± 8". The first suggests clear mild depression; the second suggests uncertainty spanning minimal to moderate.

**Trend Detection**: With uncertainty estimates, we can compute whether a change is statistically significant:

```python
change_significant = abs(score_new - score_old) > 2 * sqrt(std_new² + std_old²)
```

---

## 4. Why We Use Validated Clinical Instruments

### The Problem with Ad-Hoc Questions

Custom questions have unknown psychometric properties:
- **Reliability**: Does the question measure the same thing each time?
- **Validity**: Does the question actually measure what we think?
- **Norms**: What does a "high" score actually mean?

### The Solution: PHQ-9 and GAD-7

These instruments have been:
- Validated in dozens of studies
- Normed on thousands of patients
- Accepted by clinicians worldwide
- Mapped to clinical cutoffs

### PHQ-9 (Depression)

| Score | Severity |
|-------|----------|
| 0-4   | Minimal  |
| 5-9   | Mild     |
| 10-14 | Moderate |
| 15-19 | Moderately Severe |
| 20-27 | Severe   |

**Sensitivity**: 88% for major depression
**Specificity**: 88% for major depression

### GAD-7 (Anxiety)

| Score | Severity |
|-------|----------|
| 0-4   | Minimal  |
| 5-9   | Mild     |
| 10-14 | Moderate |
| 15-21 | Severe   |

**Sensitivity**: 89% for GAD
**Specificity**: 82% for GAD

### Data Science Rationale

Using validated instruments means:
1. **Direct clinical interpretability**: A PHQ-9 score of 15 has a defined meaning
2. **Research comparability**: Results can be compared to published literature
3. **Regulatory compliance**: Some applications require validated measures
4. **Training signal quality**: Labels based on validated instruments are more reliable

---

## 5. Why We Use a Multi-Task Neural Network

### The Problem with Separate Models

Training separate models for stress, depression, anxiety, and sleep:
- Ignores shared underlying factors
- Requires more data per target
- Cannot leverage correlations between outcomes

### The Solution: Shared Trunk with Task Heads

```
                    Shared Representation
                    (learns general features)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
        Stress Head   Depression Head   Anxiety Head
        (specific)      (specific)      (specific)
```

### Data Science Rationale

**Transfer Learning**: The shared trunk learns representations useful for all tasks. A feature that helps predict stress likely helps predict anxiety.

**Regularization**: Forcing the network to solve multiple related tasks acts as a regularizer, reducing overfitting.

**Sample Efficiency**: With 4 tasks, each backward pass provides 4× the gradient signal, effectively multiplying the dataset size.

**Correlation Modeling**: The shared representation implicitly captures that stress and anxiety are correlated. This is lost with separate models.

---

## 6. Why We Store Data in RL-Ready Format

### The Problem

Standard data storage loses:
- The context in which predictions were made
- User feedback signals
- Temporal dependencies

### The Solution: State-Action-Reward Format

```json
{
    "state": {
        "responses": {...},
        "embedding": [...],
        "previous_scores": {...}
    },
    "action": {
        "questions_shown": [...],
        "model_version": "kernel-v1.0"
    },
    "reward": {
        "user_feedback": null,
        "clinical_validation": null,
        "engagement": 0.8
    },
    "next_state": {
        "scores": {...}
    }
}
```

### Data Science Rationale

This structure enables:

1. **Offline Reinforcement Learning**: Train policies to optimize question ordering, UI design, or intervention timing

2. **Counterfactual Analysis**: "What if we had asked different questions?"

3. **Personalization**: Learn user-specific patterns over time

4. **Clinical Outcome Tracking**: Eventually link predictions to real outcomes

---

## 7. Statistical Smoothing Techniques

### The Problem

Raw model outputs can be:
- Noisy (high variance)
- Polarized (extreme predictions)
- Unstable (small input changes → big output changes)

### Solutions Implemented

#### 1. Sigmoid Scaling to Output Range

Instead of raw linear outputs, we use:
```python
output = sigmoid(raw) * (max - min) + min
```

This ensures outputs are bounded and smoothly distributed.

#### 2. Exponential Moving Average

For users with history:
```python
smoothed_score = alpha * new_score + (1 - alpha) * previous_smoothed
```

This reduces measurement noise across sessions.

#### 3. Ensemble Averaging

Multiple forward passes with dropout create an implicit ensemble:
```python
final_prediction = mean(dropout_samples)
```

This is more stable than a single forward pass.

#### 4. Calibration via Temperature Scaling

Post-hoc calibration ensures confidence matches accuracy:
```python
calibrated_prob = softmax(logits / temperature)
```

---

## 8. Visualization Design Principles

### Why These Specific Visualizations?

| Visualization | Purpose | Key Insight |
|---------------|---------|-------------|
| Radar Chart | Relative balance | Quick scan for asymmetric profiles |
| Confidence Bars | Uncertainty | Shows what the model doesn't know |
| Trend Lines | Temporal change | Tracks improvement/deterioration |
| 3D Neural Scene | Engagement | Makes the AI tangible and trustworthy |

### Data Science Considerations

**Radar Chart**: Shows all scores at once, making it easy to spot:
- High stress + low depression → situational stressor
- High everything → possible crisis
- All low → healthy baseline

**Confidence Visualization**: Users should see uncertainty because:
- Prevents over-interpretation
- Builds appropriate trust
- Encourages follow-up assessment when uncertain

**Trend Lines with Moving Average**: Raw data is noisy; showing both:
- Raw points (actual measurements)
- Smoothed line (underlying trend)

Helps users distinguish signal from noise.

---

## 9. Extensibility for Future Deep Learning

### Current Architecture Prepares For:

1. **Transformer Models**: The text embedding approach can be upgraded to fine-tuned transformers

2. **Temporal Modeling**: The RL-ready data format supports LSTM/Transformer sequence models

3. **Multi-Modal Fusion**: The architecture separates encoding (modality-specific) from prediction (shared), allowing easy addition of new modalities (e.g., sleep sensor data, activity logs)

4. **Reinforcement Learning**: 
   - State: Current responses + history
   - Action: Which question to ask next
   - Reward: User engagement + clinical outcome

5. **Federated Learning**: The modular design allows training on distributed data without centralizing sensitive information

---

## 10. Summary: Why This Architecture is Better

| Aspect | Old System | KERNEL System |
|--------|------------|---------------|
| Input | 24 binary questions | Likert + sliders + text |
| Text Processing | TF-IDF | Sentence embeddings |
| Model Output | Point estimates | Distributions with CI |
| Clinical Validity | Custom questions | PHQ-9, GAD-7 |
| Architecture | Single classifier | Multi-task network |
| Data Storage | Simple JSON | RL-ready format |
| Visualization | Basic charts | Uncertainty-aware + 3D |
| Extensibility | Limited | RL, temporal, multi-modal ready |

The KERNEL system transforms WALLS from a simple screening tool into a clinically meaningful, statistically robust, and extensible mental health assessment platform.

---

*Technical questions? See the code in `src/kernel/` or open an issue.*

