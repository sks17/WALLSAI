# Setup and Testing Guide

This document provides step-by-step instructions for setting up the WALLS project, running tests, and verifying end-to-end functionality.

---

## 1. Environment Setup

### Prerequisites
- Python 3.10+ (tested with 3.12)
- pip package manager
- Git (optional, for cloning)

### Step-by-Step Setup

```powershell
# Navigate to project directory
cd TSA_Project-main

# Create virtual environment
py -3.12 -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Or for Windows Command Prompt:
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### Verify Installation

```powershell
# Check Python version
python --version

# Check key packages
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import sklearn; print('sklearn:', sklearn.__version__)"
```

---

## 2. Data Pipeline (Optional - If Rebuilding Models)

If you need to rebuild the training data and models from scratch:

```powershell
# Step 1: Clean raw data
python src/clean_data.py

# Step 2: Build unified training dataset
python src/build_unified_dataset.py

# Step 3: Train scikit-learn models (optional, for sklearn pipeline)
python src/train_models.py

# Step 4: Train PyTorch model (recommended)
python ml/train.py
```

**Note**: Pre-trained models are already included in `ml/model.pt` and `models/`.

---

## 3. Running the Debug Test Suite

Before testing the web interface, verify the inference pipeline works correctly:

```powershell
# Run the debug inference test suite
python src/debug_inference.py
```

### Expected Output

```
======================================================================
WALLS Mental Health Model - Debug Inference Test Suite
======================================================================
Timestamp: 2025-12-05T...
Project root: C:\...\TSA_Project-main

1. Loading model schema...
   ✓ Loaded 24 features, 5 labels

2. Loading PyTorch model...
   ✓ Model loaded successfully

3. Verifying feature alignment...
   Status: ok
   ✓ Features aligned: 24 inputs
   ✓ Labels aligned: 5 outputs

4. Running test scenarios...
   ------------------------------------------------------------------
   Scenario                  Input           Prediction   Confidence
   ------------------------------------------------------------------
   neutral_baseline          0 yes / 24 no   Normal            0.8234
   anxiety_heavy             6 yes / 18 no   Anxiety           0.6543
   depression_heavy          6 yes / 18 no   Depression        0.7123
   stress_heavy              6 yes / 18 no   Stress            0.6890
   all_yes_worst_case        24 yes / 0 no   Stress            0.4521
   ------------------------------------------------------------------

5. Analysis...
   Tests run: 13
   Successful: 13
   Failed: 0

   Observations:
     ✓ Baseline correctly predicts 'Normal'
     ✓ Model produces 5 different predictions across scenarios
     ✓ Confidence range: 0.421 - 0.834
```

### What to Look For

✅ **Good Signs:**
- All tests pass (no errors)
- Baseline predicts "Normal"
- Different scenarios produce different predictions
- Confidence varies across scenarios

⚠️ **Warning Signs:**
- All scenarios predict the same class
- Very low confidence variation (<0.1 range)
- Baseline doesn't predict "Normal"

---

## 4. Running the Web Application

### Standard Mode

```powershell
# Start the Flask server
python app.py
```

Access the application at: http://127.0.0.1:5000

### Debug Mode (Recommended for Troubleshooting)

```powershell
# Enable debug logging
$env:WALLS_DEBUG = "1"

# Start the server
python app.py
```

Debug mode enables:
- Detailed logging of each prediction request
- Access to `/api/v2/debug` endpoint
- Debug panel in dashboard (Ctrl+Shift+D)

### View Logs

With debug mode enabled, you'll see detailed logs in the console:

```
============================================================
PREDICTION REQUEST RECEIVED
============================================================
2025-12-05 08:30:15 | walls.api | INFO | User ID: user_abc123
2025-12-05 08:30:15 | walls.api | INFO | Answer count: 24
2025-12-05 08:30:15 | walls.api | INFO | Feature schema loaded: 24 features expected
2025-12-05 08:30:15 | walls.api | INFO | Features matched: 24/24
2025-12-05 08:30:15 | walls.api | INFO | Yes/No distribution: 8 yes, 16 no
2025-12-05 08:30:15 | walls.api | INFO | Running PyTorch inference...
2025-12-05 08:30:15 | walls.api | INFO | Model prediction: Stress
2025-12-05 08:30:15 | walls.api | INFO | Model confidence: 0.6234
============================================================
PREDICTION COMPLETE: Stress (62.3% confidence)
============================================================
```

---

## 5. Test Scenarios

### Scenario 1: Low Stress / Normal Baseline

1. Go to http://127.0.0.1:5000/survey
2. Answer **"No"** to all questions
3. Leave free text empty or write: "I feel generally good today."
4. Submit

**Expected Result:**
- Prediction: "Normal"
- Stress score: < 20
- Depression score: < 15
- Anxiety score: < 15
- Sleep quality: > 7

### Scenario 2: High Stress Indicators

1. Go to http://127.0.0.1:5000/survey
2. Answer **"Yes"** to:
   - Do you often feel nervous or on edge?
   - Do you have trouble concentrating?
   - Is it hard to focus on tasks?
   - Are you having trouble with work or school?
   - Do stressful memories pop up unexpectedly?
   - Do you feel tired or low energy most days?
3. Answer "No" to all others
4. Write in free text: "I've been very stressed about deadlines and work pressure."
5. Submit

**Expected Result:**
- Prediction: "Stress" or "Anxiety"
- Stress score: > 40
- Confidence: > 0.5

### Scenario 3: Depression Indicators

1. Go to http://127.0.0.1:5000/survey
2. Answer **"Yes"** to:
   - Do you often feel hopeless about the future?
   - Do you often have negative thoughts about yourself?
   - Do you tend to blame yourself for things?
   - Do you feel tired or low energy most days?
   - Do you avoid people or activities you used to enjoy?
3. Answer "No" to all others
4. Write in free text: "Nothing seems to matter anymore, I feel empty inside."
5. Submit

**Expected Result:**
- Prediction: "Depression"
- Depression score: > 40
- Confidence: > 0.5

---

## 6. Using the Debug Panel

The dashboard includes a hidden debug panel for troubleshooting.

### Accessing the Debug Panel

1. Go to the dashboard: http://127.0.0.1:5000/dashboard
2. Press **Ctrl + Shift + D** to toggle the debug panel
3. The panel shows:
   - Last prediction response (JSON)
   - Last input payload
   - Backend debug info (requires WALLS_DEBUG=1)
   - API status

### Debug Panel Features

- **Last Prediction Response**: The complete JSON returned by `/api/v2/predict`
- **Backend Debug Info**: Click "Refresh Backend Debug" to see:
  - Raw payload received
  - Parsed answers
  - Feature order
  - PyTorch result
  - Any errors

---

## 7. API Testing with curl/Postman

### Test Prediction Endpoint

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/v2/predict" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{
        "answers": {
            "feeling.nervous": "yes",
            "panic": "no",
            "breathing.rapidly": "no",
            "sweating": "no",
            "trouble.in.concentration": "yes",
            "having.trouble.in.sleeping": "no",
            "having.trouble.with.work": "no",
            "hopelessness": "no",
            "anger": "no",
            "over.react": "no",
            "change.in.eating": "no",
            "suicidal.thought": "no",
            "feeling.tired": "yes",
            "close.friend": "yes",
            "social.media.addiction": "no",
            "weight.gain": "no",
            "material.possessions": "no",
            "introvert": "no",
            "popping.up.stressful.memory": "no",
            "having.nightmares": "no",
            "avoids.people.or.activities": "no",
            "feeling.negative": "no",
            "trouble.concentrating": "no",
            "blamming.yourself": "no"
        },
        "free_text": "Testing the API",
        "user_id": "test_user",
        "save": false
    }'
```

### Test Status Endpoint

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/v2/status"
```

### Test History Endpoint

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/v2/history?user_id=test_user&limit=10"
```

---

## 8. Common Issues and Solutions

### Issue: "Same scores for different inputs"

**Cause**: Model inputs not matching feature schema

**Solution**:
1. Run `python src/debug_inference.py` to verify model works
2. Check browser console for JavaScript errors
3. Enable debug logging and check if features are being matched
4. Verify survey.js SURVEY_SECTIONS IDs match schema.json features

### Issue: "ModuleNotFoundError: No module named 'X'"

**Solution**:
```powershell
# Make sure virtual environment is activated
.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Model file not found"

**Solution**:
```powershell
# Retrain the PyTorch model
python ml/train.py
```

### Issue: Extreme or unusual scores

**Possible Causes**:
1. All features being treated as "no" (check feature matching)
2. Model not trained properly (retrain with `ml/train.py`)
3. Data format mismatch (check API logs)

---

## 9. File Locations

| Purpose | Location |
|---------|----------|
| PyTorch model | `ml/model.pt` |
| Model metadata | `ml/metadata.json` |
| Feature schema | `data/schema.json` |
| Training data | `Static/Data/dataset.csv` |
| User history | `user_data/*.json` |
| API routes | `src/api.py` |
| Inference logic | `api/predict.py` |
| Survey questions | `Static/js/survey.js` |
| Visualizations | `Static/js/visualization.js` |
| API client | `Static/js/api.js` |

---

## 10. Quick Reference Commands

```powershell
# Activate environment
.venv\Scripts\Activate.ps1

# Run debug test suite
python src/debug_inference.py

# Start server (normal)
python app.py

# Start server (debug mode)
$env:WALLS_DEBUG = "1"; python app.py

# Test user store module
python src/user_store.py

# Check model schema
python -c "import json; print(json.dumps(json.load(open('ml/metadata.json')), indent=2))"
```

---

## 11. Notes & Reflections Feature

The app includes a notes feature for journaling and tracking mental health reflections.

### Testing Notes API

```powershell
# List notes (empty initially)
curl http://localhost:5000/api/notes/list -H "X-User-ID: test_user"

# Create a note
curl -X POST http://localhost:5000/api/notes/create `
  -H "Content-Type: application/json" `
  -H "X-User-ID: test_user" `
  -d '{"content": "Feeling good today after morning walk.", "tags": ["exercise", "positive"], "mood_score": 8}'

# Get available tags
curl http://localhost:5000/api/notes/tags

# Search notes
curl "http://localhost:5000/api/notes/search?q=morning" -H "X-User-ID: test_user"

# Export notes
curl "http://localhost:5000/api/notes/export?format=markdown" -H "X-User-ID: test_user"
```

### Web Interface

Navigate to: `http://localhost:5000/notes`

Features:
- Create timestamped notes with optional mood scores
- Tag notes (stress, anxiety, sleep, goals, etc.)
- Search and filter notes
- Export as JSON, Markdown, or plain text
- Pin important notes

---

## 12. Mindfulness Resources Feature

Curated mental health resources and tools.

### Testing Resources API

```powershell
# Get breathing exercises
curl http://localhost:5000/api/resources/breathing

# Get mindfulness resources
curl http://localhost:5000/api/resources/mindfulness

# Get quick tips
curl http://localhost:5000/api/resources/tips?category=anxiety

# Get educational topics
curl http://localhost:5000/api/resources/learn

# Search therapists
curl "http://localhost:5000/api/resources/search/therapist?location=near%20me"
```

### Web Interface

Navigate to: `http://localhost:5000/mindfulness`

Features:
- Guided breathing exercises with animation
- Quick mental health tips by category
- Curated meditation and mindfulness resources
- Therapist finder (opens search in new tab)
- Educational content on stress, anxiety, sleep, depression

---

## 13. WALLS Toolkit

Quick access to all features.

Navigate to: `http://localhost:5000/toolkit`

---

## 14. File Locations (Updated)

| Purpose | Location |
|---------|----------|
| PyTorch model | `ml/model.pt` |
| Model metadata | `ml/metadata.json` |
| Feature schema | `data/schema.json` |
| Training data | `Static/Data/dataset.csv` |
| User history | `user_data/*.json` |
| **User notes** | `user_data/notes/*.json` |
| API routes | `src/api.py` |
| **Notes API** | `src/notes/api.py` |
| **Resources API** | `src/resources/api.py` |
| Inference logic | `api/predict.py` |
| Survey questions | `Static/js/survey.js` |
| **Notes JS** | `Static/js/notes.js` |
| **Mindfulness JS** | `Static/js/mindfulness.js` |
| Visualizations | `Static/js/visualization.js` |
| API client | `Static/js/api.js` |

---

## 15. Mixed Input Types (Sliders + MCQ + Free Text)

The survey now supports multiple input types for improved signal quality:

### Intensity Sliders (0-100 Scale)

Three questions use intensity sliders instead of yes/no:

1. **Hopelessness/Motivation**
   - Question: "How much have you been experiencing feelings of reduced optimism or motivation recently?"
   - Range: 0 (Not at all) → 100 (Extremely)

2. **Anger/Frustration**
   - Question: "How much frustration or irritability have you been experiencing recently?"
   - Range: 0 (Not at all) → 100 (Extremely)

3. **Energy/Fatigue**
   - Question: "How much fatigue or low energy have you been experiencing recently?"
   - Range: 0 (Not at all) → 100 (Extremely)

### Backwards Compatibility

- Slider values are converted to yes/no for the PyTorch model (threshold: 50)
- Raw intensity values (0-100) are stored separately as `*_intensity` fields
- Existing answers (yes/no) continue to work unchanged

### Free-Text Fields

Two free-text input fields are now available:

1. **General Reflections** (existing): "Is there anything else on your mind?"
2. **Wellbeing Influences** (new): "In your own words, describe anything that has been influencing your wellbeing recently."

Both fields are combined and processed by the KERNEL text encoder.

### Data Storage

User evaluations now include:
```json
{
  "input": { ... standard yes/no answers ... },
  "intensity_values": {
    "hopelessness_intensity": 65,
    "anger_intensity": 30,
    "feeling.tired_intensity": 80
  },
  "free_text": "Combined text from both free-text fields",
  "scores": { ... predictions ... }
}
```

### Dashboard Visualization

New intensity charts on the dashboard:
- **Intensity Over Time**: Line chart showing slider values across evaluations
- **Response Distribution**: Histogram showing frequency of intensity ranges

### Testing Instructions

```powershell
# Start the app
python app.py

# Take a survey and use the sliders:
# 1. Navigate to /survey
# 2. Answer yes/no questions as normal
# 3. Use the sliders for the 3 intensity questions
# 4. Fill in both free-text fields
# 5. Submit and verify:
#    - Dashboard shows intensity charts
#    - User history includes intensity_values
#    - Predictions still work correctly
```

---

## 16. Safety Layer & Medical Disclaimers

WALLS includes comprehensive safety features to ensure responsible use:

### Universal Footer (all pages)
- Disclaimer: "WALLS is not a medical service..."
- Crisis hotlines: 988 Lifeline, International resources
- Links to opencounseling.com/suicide-hotlines

### Floating Help Badge
- "Need help?" badge in bottom-right corner
- Expands to show emergency resources
- Quick access to 988, Crisis Text Line, mindfulness tools

### Page-Specific Disclaimers
All key pages include disclaimer banners:
- **Survey**: "This survey provides personal insights..."
- **Dashboard**: "The insights below are for personal awareness..."
- **Notes**: "Your notes are stored locally..."
- **Resources**: Crisis banner prominently displayed

### Liability-Safe Question Wording
Survey questions use observational, non-clinical phrasing:
- ❌ "Do you feel hopeless?" 
- ✅ "Recently, have you been inclined toward feelings of reduced optimism?"

### ARIA Tooltips
Each survey question includes a tooltip explaining:
- "Your answers help WALLS reflect patterns, not evaluate medical conditions."

### Sensitive Question Handling
Questions about self-harm include:
- Visual indicator (gentle highlight)
- Inline crisis resources
- "If you're struggling, please reach out: Call 988"

### Security Note for Free Text
Text input areas display:
- "WALLS does not store or infer identifiable personal information"
- "Avoid including personal names, addresses, or identifying details"

### Testing Safety Features

```powershell
# Start the app
python app.py

# Check these elements:
# 1. Footer visible on all pages
# 2. Floating help badge in bottom-right
# 3. Survey disclaimer at top
# 4. Question tooltips (hover over ?)
# 5. Sensitive question styling on self-harm question
# 6. Security note on free-text input
```

---

*Last updated: December 2025*

