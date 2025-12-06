# WALLS AI Model Explanation

## Overview

WALLS (Wellness And Lifestyle Learning System) uses machine learning to analyze self-reported mental health symptoms and provide insights about potential mental health states. This document explains what data the models were trained on, what the outputs mean, and how to interpret the results.

> ⚠️ **Important Disclaimer**: WALLS is **not a medical diagnostic tool**. It is designed as a self-reflection aid that identifies patterns in self-reported symptoms. Always consult a qualified healthcare professional for proper diagnosis and treatment of mental health conditions.

---

## 1. Training Data

### Primary Dataset: `Static/Data/dataset.csv`

The PyTorch model is trained on a symptom-disorder dataset with the following structure:

| Feature Type | Features |
|--------------|----------|
| **Anxiety Symptoms** | feeling.nervous, panic, breathing.rapidly, sweating |
| **Concentration** | trouble.in.concentration, trouble.concentrating |
| **Sleep Issues** | having.trouble.in.sleeping, having.nightmares |
| **Work/Functioning** | having.trouble.with.work |
| **Depression Signs** | hopelessness, suicidal.thought, feeling.tired, feeling.negative, blamming.yourself |
| **Emotional Regulation** | anger, over.react |
| **Eating/Weight** | change.in.eating, weight.gain |
| **Social Behavior** | close.friend, social.media.addiction, introvert, avoids.people.or.activities |
| **Stress Indicators** | popping.up.stressful.memory |
| **Other** | material.possessions |

**Target Labels**: Anxiety, Depression, Loneliness, Stress, Normal

Each row represents a person's symptom profile (24 yes/no answers) and their associated mental health state.

### Unified Dataset (for scikit-learn models)

The unified training pipeline combines multiple research datasets:

1. **Abadi Socio-Psychological COVID Data**: Demographic and lifestyle factors related to mental health during COVID-19
2. **mmc2 (PHQ-9/GAD-7)**: Clinical screening questionnaire responses for depression and anxiety
3. **mental_health_finaldata_1**: Lifestyle and stress survey data
4. **pone_stress**: COVID-related stress factor assessments
5. **Legacy dataset.csv**: Symptom-disorder mappings

These are merged into `unified_dataset/unified_training.csv` with standardized columns.

---

## 2. What Each Output Means

### Prediction Categories

The PyTorch model predicts one of five categories based on symptom patterns:

| Category | Description | Typical Symptom Pattern |
|----------|-------------|-------------------------|
| **Anxiety** | Elevated worry, fear, and physical symptoms | Nervousness, panic, rapid breathing, sweating, trouble concentrating |
| **Depression** | Persistent low mood and loss of interest | Hopelessness, fatigue, negative thoughts, self-blame, sleep issues |
| **Loneliness** | Social isolation and disconnection | Avoidance of people/activities, introversion, social media overuse, lacking close friends |
| **Stress** | Overwhelm and difficulty coping | Work trouble, stressful memories, anger, overreacting, eating changes |
| **Normal** | No significant symptom patterns detected | Mostly "no" responses across symptom categories |

### Numeric Scores

The model outputs probabilities (0-1) for each category, which are converted to percentage scores (0-100) for display:

| Score | Scale | Interpretation |
|-------|-------|----------------|
| **stress_score** | 0-100 | Probability × 100 that stress is the dominant pattern |
| **depression_score** | 0-100 | Probability × 100 that depression is the dominant pattern |
| **anxiety_score** | 0-100 | Probability × 100 that anxiety is the dominant pattern |
| **sleep_quality** | 0-10 | Derived metric: higher = better sleep (inversely related to stress + anxiety) |

### Score Interpretation Guide

**Stress Score:**
- 0-20: Low stress indicators
- 20-40: Moderate stress indicators
- 40-70: Elevated stress indicators (consider stress management techniques)
- 70+: High stress indicators (strongly consider professional consultation)

**Depression Score:**
- 0-10: Minimal indicators
- 10-25: Mild indicators
- 25-50: Moderate indicators (consider reaching out to a professional)
- 50+: Significant indicators (professional consultation recommended)

**Anxiety Score:**
- 0-15: Minimal indicators
- 15-30: Mild indicators
- 30-50: Moderate indicators (consider relaxation techniques)
- 50+: Elevated indicators (professional consultation recommended)

**Sleep Quality:**
- 8-10: Good sleep indicators
- 5-8: Fair sleep quality
- 2-5: Poor sleep indicators
- 0-2: Significantly impaired sleep (may need attention)

---

## 3. How the Model Works

### Input Processing

1. **Survey Answers → Feature Vector**
   
   The survey collects 24 yes/no answers. Each is converted to binary:
   ```
   "yes" → 1.0
   "no"  → 0.0
   ```
   
   This creates a 24-dimensional input vector.

2. **Free Text (Optional)**
   
   If provided, free-text input is processed by a TF-IDF vectorizer that converts words into numerical features based on their frequency and importance. This is concatenated with the survey features.

### Model Architecture (PyTorch)

```
Input Layer (24 features)
    ↓
Hidden Layer 1 (64 neurons) + ReLU + Dropout
    ↓
Hidden Layer 2 (32 neurons) + ReLU + Dropout
    ↓
Hidden Layer 3 (16 neurons) + ReLU + Dropout
    ↓
Output Layer (5 classes) + Softmax
    ↓
Probabilities for [Anxiety, Depression, Loneliness, Stress, Normal]
```

The model uses:
- **ReLU activation**: Allows non-linear pattern recognition
- **Dropout (10%)**: Prevents overfitting during training
- **Softmax output**: Converts raw scores to probabilities that sum to 1.0

### Prediction Flow

```
User Survey Responses
    ↓
24 Yes/No → Binary Vector [0,1,1,0,...]
    ↓
MLPClassifier Forward Pass
    ↓
5 Probability Outputs [0.12, 0.08, 0.05, 0.72, 0.03]
    ↓
Highest Probability = Prediction ("Stress")
    ↓
Convert to Display Scores (× 100)
```

---

## 4. How to Interpret the Graphs

### Radar Chart

The radar chart displays all four scores on a "spider web" layout:

- **Axes**: Stress, Depression, Anxiety, Sleep (clockwise)
- **Shape**: Larger area = more indicators across categories
- **Ideal shape**: Small, centered (low scores across all categories)
- **Concerning shape**: Extended toward one or more axes

### Line Chart (Trend)

Shows how each score changes over time:

- **X-axis**: Time (date of each survey)
- **Y-axis**: Score value (0-100)
- **Lines**: One color per metric
- **Interpretation**: Rising lines = worsening indicators; Falling lines = improvement

### Bar Chart

Compares current scores to previous or average:

- **Height**: Score magnitude
- **Color coding**: Green (low), Yellow (moderate), Red (elevated)
- **Use**: Quick comparison of relative severity

### Gauges

Visual severity indicators:

- **Fill level**: Score percentage
- **Color zones**: Typically green → yellow → orange → red
- **Use**: At-a-glance severity check

---

## 5. Limitations and Caveats

### What This Is
- A **pattern recognition tool** that identifies symptom clusters
- A **self-reflection aid** to encourage mindfulness about mental health
- A **tracking system** to observe changes over time

### What This Is NOT
- **Not a diagnostic tool**: Cannot diagnose mental health conditions
- **Not a substitute for professional help**: Always consult qualified professionals
- **Not 100% accurate**: Model predictions are probabilistic, not definitive
- **Not personalized to you**: Trained on general population data

### Known Limitations

1. **Binary simplification**: Mental health exists on spectrums, but the model uses yes/no inputs
2. **Cultural bias**: Training data may not represent all populations equally
3. **Self-report bias**: Accuracy depends on honest and accurate self-reporting
4. **Temporal limitation**: Captures a snapshot in time, not ongoing states
5. **No clinical validation**: This tool has not been validated in clinical settings

---

## 6. When to Seek Help

Please consult a mental health professional if:

- You consistently score high (>50) on depression or anxiety
- You have thoughts of self-harm (answer "yes" to suicidal.thought)
- Your scores are significantly impacting daily functioning
- You've noticed persistent worsening trends over time
- You feel you need support beyond self-reflection

**Crisis Resources:**
- National Suicide Prevention Lifeline: 988 (US)
- Crisis Text Line: Text HOME to 741741 (US)
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

---

## 7. Future Improvements

The system is designed to be extensible:

- **Reinforcement Learning**: User feedback could help personalize predictions
- **Temporal Modeling**: LSTM/Transformer models could capture patterns over time
- **Multi-modal Input**: Voice, activity data, or other signals could be incorporated
- **Clinical Integration**: With proper validation, could support clinical workflows

---

*Last updated: December 2025*

