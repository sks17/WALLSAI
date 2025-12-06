# WALLS Frontend Upgrade Guide

## Overview

This document describes the upgraded WALLS (Wellness App) frontend with advanced AI visualizations, dynamic surveys, and integrated ML inference.

---

## Architecture

### Dual Aesthetic Design

The frontend implements a **dual aesthetic** that creates visual narrative:

1. **Mental Health UI (Calm)**
   - Soft pastel colors (lavender, cream, dusty pink)
   - Generous whitespace
   - Rounded corners, subtle glows
   - Slow fade-in animations
   - Used in: Landing, Login, Survey forms, Dashboard containers

2. **AI Visualization Layer (Tech/Geeky)**
   - Dark mode with neon accents (cyan/magenta/purple)
   - Animated 3D objects (Three.js)
   - Shader-like effects
   - Grid backgrounds, scanlines
   - Used in: AI Deep Visualization Zone

This contrast tells a story: *"Your inner world (calm) vs. the AI engine (complex analysis)"*

---

## New Files Created

### CSS

| File | Purpose |
|------|---------|
| `Static/css/ai-visuals.css` | Dark neon aesthetic for AI visualizations |

### JavaScript

| File | Purpose |
|------|---------|
| `Static/js/api.js` | API wrapper for `/api/v2/*` endpoints |
| `Static/js/survey.js` | Dynamic survey with sliders, dropdowns, yes/no, text |
| `Static/js/visualization.js` | Three.js 3D + Chart.js 2D visualizations |

### Templates

| File | Purpose |
|------|---------|
| `templates/ai_section.html` | Reusable AI visualization partial |
| `templates/dashboard.html` | Redesigned dashboard with AI zone |
| `templates/survey.html` | Dynamic survey interface |

### Data Storage

| Directory | Purpose |
|-----------|---------|
| `user_data/` | Stores evaluation history as JSON |

---

## JavaScript Modules

### WallsAPI (`api.js`)

API wrapper providing clean interface to backend endpoints.

```javascript
// Run ML inference
const result = await WallsAPI.predict(userFeatures, freeText, userId);

// Get evaluation history
const history = await WallsAPI.getHistory(userId, limit);

// Get computed metrics
const metrics = await WallsAPI.getMetrics(userId);

// Get clinical thresholds
const thresholds = await WallsAPI.getThresholds();

// Check API status
const status = await WallsAPI.getStatus();

// Local storage utilities
const userId = WallsAPI.getUserId();
WallsAPI.saveLocalEntry(entry);
const localHistory = WallsAPI.getLocalHistory();

// Data processing
const timeSeries = WallsAPI.computeTimeSeries(history, 'stress_score');
const movingAvg = WallsAPI.computeMovingAverage(values, window);
const anomalies = WallsAPI.detectAnomalies(values, threshold);

// Event subscription
const unsubscribe = WallsAPI.onPrediction((result) => {
  console.log('New prediction:', result);
});
```

### WallsSurvey (`survey.js`)

Dynamic survey system with multiple input types.

```javascript
// Initialize survey
WallsSurvey.init('container-id', {
  onSubmit: (result, features, freeText) => {
    console.log('Survey completed:', result);
  }
});

// Reset survey
WallsSurvey.reset();

// Get current responses
const responses = WallsSurvey.getResponses();
```

**Survey Sections:**
1. Demographics (dropdowns)
2. Emotional State (sliders 0-4)
3. Physical Wellbeing (yes/no, sliders)
4. Symptom Check (yes/no)
5. Free Response (textarea)

### WallsVisualizations (`visualization.js`)

Combined 3D + 2D visualization system.

```javascript
// Initialize
await WallsVisualizations.init();

// 3D Visualizations (Three.js)
await WallsVisualizations.createPointCloud('canvas-id');
await WallsVisualizations.createHyperplane('canvas-id');
await WallsVisualizations.createMentalSphere('canvas-id');

// 2D Charts (Chart.js)
await WallsVisualizations.createRadarChart('canvas-id');
await WallsVisualizations.createTrendChart('canvas-id');
await WallsVisualizations.createComparisonChart('canvas-id');
await WallsVisualizations.createGaugeChart('canvas-id', 'stress');

// Update scores (triggers visualization updates)
WallsVisualizations.updateScores({
  stress: 15,
  depression: 8,
  anxiety: 12,
  sleep: 7
});

// Refresh data from API
await WallsVisualizations.refreshData();

// Cleanup
WallsVisualizations.destroy();
```

---

## API Endpoints

All endpoints are available at `/api/v2/*`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/predict` | POST | Run ML inference |
| `/api/v2/history` | GET | Get evaluation history |
| `/api/v2/metrics` | GET | Get computed metrics |
| `/api/v2/thresholds` | GET | Get clinical thresholds |
| `/api/v2/status` | GET | Check API/model status |

### Predict Endpoint

**Request:**
```json
{
  "answers": {
    "age": "25-30",
    "gender": "Male",
    "mood_swings": "High",
    "frustration": "Yes",
    ...
  },
  "free_text": "Optional text about how the user is feeling...",
  "user_id": "user_123",
  "save": true
}
```

**Response:**
```json
{
  "scores": {
    "stress_score": 15.2,
    "depression_score": 8.7,
    "anxiety_score": 12.1,
    "sleep_quality": 6.3
  },
  "classifications": {
    "stress_score": "moderate",
    "depression_score": "mild",
    "anxiety_score": "moderate",
    "sleep_quality": "fair"
  },
  "evaluation_id": "abc123"
}
```

---

## 3D Visualizations

### Point Cloud (Emotional Embedding Space)
- 500 particles representing emotional state vectors
- Colors shift based on dominant score
- Slow rotation with depth-of-field effect
- Particles move based on stress level

### Hyperplane (Decision Boundaries)
- 4 planes representing model decision surfaces
- Planes rotate/skew based on scores
- Orbiting camera view
- Grid overlay with neon outlines

### Mental State Sphere
- Icosahedron with wireframe
- **Radius** = Stress level
- **Vibration** = Anxiety level
- **Glow intensity** = Depression level
- **Color hue** = Sleep quality
- Real-time morphing shader-like effect

---

## 2D Charts

### Radar Chart
- Multi-dimensional view of all 4 scores
- Updates in real-time on new predictions
- Color-coded points per metric

### Trend Line Chart
- Time-series of all metrics
- Multiple datasets with different colors
- Smooth tension curves

### Bar Comparison
- Current vs. Previous evaluation
- Side-by-side bars per metric
- Clear visual delta

### Gauge Charts
- Semi-circle doughnut for single metric
- Severity-aware coloring
- Numeric value display

---

## Dashboard Sections

### Section A: Quick Stats
- 4 stat cards with icons
- Real-time score display
- Hover effects

### Section B: AI Deep Visualization Zone
- Dark container with scanline animation
- Score meters with animated fill bars
- 3D visualizations in grid layout
- 2D charts for statistical analysis
- Anomaly detection alerts

### Section C: Emotional Trajectory
- Moving averages analysis
- Pattern detection insights
- Personalized recommendations
- Medical disclaimer

### Section D: Evaluation History
- Chronological list of past evaluations
- Score badges per metric
- Timestamps and predictions

---

## Survey Flow

```
┌─────────────────┐
│  1. Demographics │
│  (age, gender,   │
│   occupation)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Emotional   │
│  State          │
│  (sliders 0-4)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Physical    │
│  Wellbeing      │
│  (yes/no, slider)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Symptom     │
│  Check          │
│  (yes/no)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Free Text   │
│  (optional)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  POST /api/v2/  │
│  predict        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Show Results   │
│  Redirect to    │
│  Dashboard      │
└─────────────────┘
```

---

## Data Storage Format

Evaluations are stored in `user_data/{user_id}.json`:

```json
[
  {
    "id": "abc12345",
    "user_id": "user_123",
    "timestamp": "2025-12-05T10:30:00.000Z",
    "input": {
      "age": "25-30",
      "mood_swings": "Medium",
      ...
    },
    "free_text": "Feeling stressed about work...",
    "scores": {
      "stress_score": 15.2,
      "depression_score": 8.7,
      "anxiety_score": 12.1,
      "sleep_quality": 6.3
    }
  }
]
```

### RL-Ready Structure

For future reinforcement learning integration:

```json
{
  "policy": {
    "state": "{\"scores\": {...}, \"input_count\": 15}",
    "reward": null,
    "next_question": null
  }
}
```

---

## CSS Variables

### Calm Theme (styles.css)
```css
:root {
  --bg: #fbfaf7;
  --card: #ffffff;
  --primary: #5fafbf;
  --secondary: #c7b8e6;
  --text: #2d2d2d;
  --muted: #666666;
}
```

### AI Theme (ai-visuals.css)
```css
:root {
  --ai-cyan: #00f5ff;
  --ai-magenta: #ff00ff;
  --ai-purple: #8b5cf6;
  --ai-bg-dark: #0a0a0f;
  --ai-bg-card: #12121a;
  --ai-text-primary: #e0e0e0;
}
```

---

## Integration Checklist

- [x] Flask blueprints registered in `app.py`
- [x] API endpoints at `/api/v2/*`
- [x] CDN dependencies (Three.js, Chart.js) loaded dynamically
- [x] User data stored in `user_data/`
- [x] CORS enabled for API access
- [x] Templates extend `base.html`
- [x] AI section included via `{% include 'ai_section.html' %}`
- [x] Survey serializes to API-compatible format
- [x] Visualizations update on prediction events

---

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Train models (if not already done)
python src/train_models.py

# Run Flask app
python app.py

# Visit
# Landing: http://localhost:5000/
# Login: http://localhost:5000/login
# Dashboard: http://localhost:5000/dashboard
# Survey: http://localhost:5000/survey
```

---

## Future Enhancements

1. **Real-time WebSocket Updates**
   - Push prediction results to all clients
   - Live dashboard collaboration

2. **RL Question Selection**
   - Use RL policy to select next question
   - Adaptive survey flow based on responses

3. **Sentiment Analysis Enhancement**
   - Better TF-IDF features from free text
   - Emotion detection from text

4. **User Authentication**
   - Replace mock auth with Firebase
   - Persistent user profiles

5. **More Visualizations**
   - Heatmap of weekly patterns
   - Comparison with population averages
   - 3D trajectory through time

---

## Troubleshooting

### Visualizations Not Loading
- Check browser console for Three.js/Chart.js CDN errors
- Ensure canvas elements have proper IDs
- Verify `WallsVisualizations.init()` is called

### API Returning Errors
- Check if models are trained (`models/*.pkl`)
- Verify `src/inference.py` imports succeed
- Check Flask logs for detailed errors

### Survey Not Submitting
- Ensure all required fields are filled
- Check browser console for validation errors
- Verify `/api/v2/predict` endpoint is accessible

---

## Dependencies

### Python
- Flask
- Flask-CORS
- pandas
- numpy
- scikit-learn
- (optional) torch for PyTorch models

### Frontend (CDN)
- Three.js r128
- Chart.js 4.x
- JetBrains Mono font

---

*WALLS - Support. Wherever. Whenever.*

