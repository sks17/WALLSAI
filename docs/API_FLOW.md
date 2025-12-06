# API Flow Documentation

## Overview

This document traces the complete end-to-end flow from user interaction to prediction result display.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  survey.html                                                                 │
│       │                                                                      │
│       ▼                                                                      │
│  WallsSurvey.init()                                                          │
│       │ Renders 24 Yes/No questions from SURVEY_SECTIONS                     │
│       │ Features match: schema.json (feeling.nervous, panic, etc.)           │
│       ▼                                                                      │
│  User clicks Submit                                                          │
│       │                                                                      │
│       ▼                                                                      │
│  handleSubmit()                                                              │
│       │ collectAllResponses()                                                │
│       │ mapFeaturesToMLFormat() → lowercase yes/no                           │
│       │                                                                      │
│       ▼                                                                      │
│  WallsAPI.predict(features, freeText, userId)                                │
│       │                                                                      │
│       │ POST /api/v2/predict                                                 │
│       │ Body: {                                                              │
│       │   "answers": {"feeling.nervous": "yes", "panic": "no", ...},         │
│       │   "free_text": "I feel tired...",                                    │
│       │   "user_id": "user_abc123",                                          │
│       │   "save": true                                                       │
│       │ }                                                                    │
│       │                                                                      │
└───────┼──────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  src/api.py :: predict()                                                     │
│       │                                                                      │
│       │ 1. Parse JSON payload                                                │
│       │ 2. Get feature_order from ml/metadata.json                           │
│       │ 3. Convert answers dict → ordered list (24 yes/no values)            │
│       │                                                                      │
│       ▼                                                                      │
│  api/predict.py :: pytorch_run_inference(answers_list)                       │
│       │                                                                      │
│       │ 1. Load metadata (features, labels, config)                          │
│       │ 2. Create Preprocessor from schema                                   │
│       │ 3. Encode yes/no → binary tensor [0,1] (shape: 1×24)                 │
│       │ 4. Load MLPClassifier from ml/model.pt                               │
│       │                                                                      │
│       ▼                                                                      │
│  ml/model.py :: MLPClassifier                                                │
│       │                                                                      │
│       │ Architecture:                                                        │
│       │   Input: 24 features                                                 │
│       │   Hidden: [64, 32, 16] with ReLU + Dropout                           │
│       │   Output: 5 classes (Anxiety, Depression, Loneliness, Stress, Normal)│
│       │                                                                      │
│       │ Returns: softmax probabilities for each class                        │
│       │                                                                      │
│       ▼                                                                      │
│  Response Construction                                                       │
│       │                                                                      │
│       │ {                                                                    │
│       │   "prediction": "Stress",           // Highest probability class     │
│       │   "confidence": 0.7234,              // Probability of prediction    │
│       │   "probabilities": {                                                 │
│       │     "Anxiety": 0.12,                                                 │
│       │     "Depression": 0.08,                                              │
│       │     "Loneliness": 0.05,                                              │
│       │     "Stress": 0.72,                                                  │
│       │     "Normal": 0.03                                                   │
│       │   },                                                                 │
│       │   "scores": {                        // Derived for visualization    │
│       │     "stress_score": 72.34,           // probability * 100            │
│       │     "depression_score": 8.0,                                         │
│       │     "anxiety_score": 12.0,                                           │
│       │     "sleep_quality": 6.3             // Inverse of stress+anxiety    │
│       │   },                                                                 │
│       │   "classifications": {...},                                          │
│       │   "evaluation_id": "abc123"                                          │
│       │ }                                                                    │
│       │                                                                      │
└───────┼──────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND RESPONSE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  survey.js :: showSuccess(result)                                            │
│       │ Display scores in summary cards                                      │
│       │ Auto-redirect to /dashboard                                          │
│       │                                                                      │
│       ▼                                                                      │
│  dashboard.html                                                              │
│       │ WallsVisualization.init()                                            │
│       │ Fetches /api/v2/history and /api/v2/metrics                          │
│       │                                                                      │
│       ▼                                                                      │
│  visualization.js                                                            │
│       │ - updateRadarChart(scores)                                           │
│       │ - updateBarChart(scores)                                             │
│       │ - updateTrendLines(history)                                          │
│       │ - updateGauges(scores)                                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Detailed JSON Structure

### Request: POST /api/v2/predict

```json
{
  "answers": {
    "feeling.nervous": "yes",
    "panic": "no",
    "breathing.rapidly": "no",
    "sweating": "yes",
    "trouble.in.concentration": "yes",
    "having.trouble.in.sleeping": "yes",
    "having.trouble.with.work": "no",
    "hopelessness": "no",
    "anger": "yes",
    "over.react": "no",
    "change.in.eating": "yes",
    "suicidal.thought": "no",
    "feeling.tired": "yes",
    "close.friend": "yes",
    "social.media.addiction": "no",
    "weight.gain": "no",
    "material.possessions": "no",
    "introvert": "yes",
    "popping.up.stressful.memory": "no",
    "having.nightmares": "no",
    "avoids.people.or.activities": "no",
    "feeling.negative": "yes",
    "trouble.concentrating": "yes",
    "blamming.yourself": "no"
  },
  "free_text": "I've been feeling stressed about work lately.",
  "user_id": "user_abc123",
  "save": true
}
```

### Response: 200 OK

```json
{
  "prediction": "Stress",
  "confidence": 0.7234,
  "probabilities": {
    "Anxiety": 0.1234,
    "Depression": 0.0845,
    "Loneliness": 0.0512,
    "Stress": 0.7234,
    "Normal": 0.0175
  },
  "scores": {
    "stress_score": 72.34,
    "depression_score": 8.45,
    "anxiety_score": 12.34,
    "sleep_quality": 6.23
  },
  "classifications": {
    "stress_score": "high",
    "depression_score": "minimal",
    "anxiety_score": "minimal",
    "sleep_quality": "good"
  },
  "evaluation_id": "a1b2c3d4"
}
```

## Frontend Data Transformations

### survey.js: mapFeaturesToMLFormat()

```javascript
// Input from Yes/No buttons
{ "feeling.nervous": "Yes", "panic": "No" }

// Output (lowercase for model)
{ "feeling.nervous": "yes", "panic": "no" }
```

### api.js: predict()

```javascript
WallsAPI.predict(features, freeText, userId) 
→ POST /api/v2/predict
→ { answers: features, free_text: freeText, user_id: userId, save: true }
```

## Backend Data Transformations

### src/api.py: convert_answers_to_list()

```python
# Input: dict of answers
{"feeling.nervous": "yes", "panic": "no", ...}

# Feature order from schema.json
["feeling.nervous", "panic", "breathing.rapidly", ...]

# Output: ordered list
["yes", "no", "no", "no", ...]  # 24 items
```

### api/predict.py: Preprocessor.encode_answers()

```python
# Input: list of yes/no strings
["yes", "no", "no", ...]

# Output: PyTorch tensor
tensor([[1.0, 0.0, 0.0, ...]])  # shape: (1, 24)
```

## Debugging Entry Points

1. **Browser Console**: Check `WallsAPI` calls with `console.debug`
2. **Flask Logs**: Enable DEBUG level logging in `src/api.py`
3. **Test Harness**: Run `python src/debug_inference.py`

## Enabling Debug Logging

Set environment variable or modify `app.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or run Flask in debug mode:

```bash
set FLASK_DEBUG=1
python app.py
```

## Common Issues

1. **Same outputs for different inputs**: Check if answers are being matched to schema features
2. **Extreme scores**: Model outputs are probabilities (0-1), converted to percentages (0-100)
3. **Missing features**: Features not in schema.json are ignored, defaulting to "no"

