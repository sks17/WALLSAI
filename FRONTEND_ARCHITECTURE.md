# Frontend Architecture Summary

## Overview

The WALLS (Wellness App) frontend is a Flask-templated web application with a **calm, wellness-oriented aesthetic**. It uses Jinja2 templates with a shared base layout, custom CSS with CSS variables, and vanilla JavaScript for interactivity.

**Branding:** "WALLS" — *Support. Wherever. Whenever.*

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Templating | Jinja2 (Flask) |
| Styling | Custom CSS with CSS variables |
| JavaScript | Vanilla JS (no framework) |
| Charts | Chart.js (available via `visualization.js`) |
| Auth | Mock authentication (placeholder for Firebase) |
| State | Flask sessions + in-memory store |

---

## Directory Structure

```
templates/
├── base.html          # Root template (header, splash, accessibility)
├── index.html         # Landing page
├── login.html         # Login form
├── dashboard.html     # User dashboard with history
├── survey.html        # Mental health questionnaire
└── (legacy)           # aid.html, calendar.html, exercise.html, etc.

Static/
├── css/
│   └── styles.css     # Global styles (691 lines)
└── js/
    ├── accessibility.js      # Text size, colorblind, high-contrast controls
    ├── firebase-placeholder.js   # Mock auth placeholder
    └── visualization.js      # Chart.js helpers for dashboard visualizations
```

---

## Template Hierarchy

```
base.html
├── index.html         (Landing page)
├── login.html         (Authentication)
├── dashboard.html     (User home)
└── survey.html        (Questionnaire)
```

### `base.html` — Root Template

The shared layout providing:

1. **Splash Screen** — Animated logo on page load
   - First visit: Click "WALLS" to dismiss, shows catchphrase
   - Repeat visits: Auto-dismiss after 3.2s, no catchphrase

2. **Header** — Site branding + accessibility controls
   ```
   [WALLS logo] [Brand title]     [Page actions] [Accessibility]
   ```

3. **Accessibility Panel** — Dropdown with:
   - Text size: Normal / Large / Extra Large
   - Colorblind-friendly mode
   - High contrast mode
   - Reset button

4. **Character Animation** — Titles with `data-animate="chars"` fade in letter-by-letter

**Template Blocks:**
- `{% block title %}` — Page title
- `{% block head_extra %}` — Additional `<head>` content
- `{% block header_actions %}` — Header navigation buttons
- `{% block content %}` — Main page content
- `{% block body_extra %}` — Additional scripts

---

## Page-by-Page Breakdown

### 1. Landing Page (`index.html`)

**Route:** `/` (served by legacy or index route)

**Features:**
- Hero section with animated title
- "Start now" and "Take a survey" CTAs
- Feature cards: Clarity, Calm design, Ready for growth

**Template Structure:**
```html
<section class="hero">
  <h1 data-animate="chars">Your calm space for mental wellness</h1>
  <p>Take a moment. Breathe. Let's begin.</p>
  <div class="hero-actions">
    <a href="/login">Start now</a>
    <a href="/survey">Take a survey</a>
  </div>
</section>

<section class="journey-section">
  <!-- Feature cards -->
</section>
```

---

### 2. Login Page (`login.html`)

**Route:** `GET/POST /login`

**Features:**
- Hero with animated title
- Email/password form in a soft card
- Mock authentication (any credentials work)
- Redirects to dashboard on success

**Form Submission:**
1. Client calls `mockAuthLogin()` (placeholder)
2. Form POSTs to `/login`
3. Backend stores email in `session["user_email"]`
4. Redirects to `/dashboard`

**Template Structure:**
```html
<section class="hero">
  <h1>Welcome to Your Mental Health Journey</h1>
</section>

<section class="journey-section">
  <div class="soft-card auth-card">
    <form action="/login" method="post">
      <input name="email" type="email" required>
      <input name="password" type="password" required>
      <button type="submit">Login</button>
    </form>
  </div>
</section>
```

---

### 3. Dashboard (`dashboard.html`)

**Route:** `GET /dashboard` (requires login)

**Features:**
- Personalized greeting with user email
- "Recent trends" placeholder
- Survey history list (from in-memory store)
- "Take Survey" button in header

**Data Passed to Template:**
```python
render_template("dashboard.html",
    user_email=email,
    history=user_data["history"]
)
```

**History Display:**
```html
{% for item in history|reverse %}
  <li>
    <strong>{{ item.prediction }}</strong>
    <span>({{ item.confidence }})</span>
    <div>{{ item.timestamp }}</div>
  </li>
{% endfor %}
```

---

### 4. Survey Page (`survey.html`)

**Route:** `GET /survey` (requires login)

**Features:**
- 24 Yes/No questions loaded from `data/schema.json`
- Each question in a `<fieldset>` with radio buttons
- Form submits to `/survey-submit`
- Accessible with `aria-describedby` hints

**Questions Source:**
```python
schema = load_schema()  # from data/schema.json
features = schema["features"]  # 24 symptom questions
```

**Template Loop:**
```html
{% for feature in features %}
  <fieldset class="question">
    <legend>{{ feature | capitalize }}</legend>
    <label><input type="radio" name="q_{{ loop.index0 }}" value="yes"> Yes</label>
    <label><input type="radio" name="q_{{ loop.index0 }}" value="no"> No</label>
  </fieldset>
{% endfor %}
```

**Submission Flow:**
1. User answers all 24 questions
2. Form POSTs to `/survey-submit`
3. Backend runs inference via `run_inference(answers)`
4. Result stored in user's history
5. Redirects to dashboard with flash message

---

## CSS Architecture

### Design System

**Color Palette:**
```css
:root {
  --bg: #fbfaf7;           /* Soft off-white background */
  --card: #ffffff;         /* Card surfaces */
  --primary: #5fafbf;      /* Muted teal (CTAs) */
  --secondary: #c7b8e6;    /* Pastel lavender */
  --text: #2d2d2d;         /* Dark gray text */
  --muted: #666666;        /* Secondary text */
  --border: #dfe5ea;       /* Subtle borders */
}
```

**Typography:**
```css
--font: "Inter", "Segoe UI", system-ui, sans-serif;      /* Body */
--display-font: "Helvetica Neue", "Helvetica", Arial;    /* Titles */
```

**Spacing & Rounding:**
```css
--radius: 12px;       /* Standard corners */
--radius-lg: 18px;    /* Large cards */
--shadow: 0 14px 32px rgba(0, 0, 0, 0.07);
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `.hero` | Full-width hero section with centered content |
| `.soft-card` | White card with rounded corners and shadow |
| `.btn-primary` | Teal primary action button |
| `.btn-ghost` | Transparent secondary button |
| `.fade-in` | Fade-in animation on load |
| `.fade-chars` | Character-by-character title animation |
| `.journey-section` | Padded content section |
| `.form-field` | Form input with label |
| `.question` | Survey question fieldset |

### Accessibility Modes

**Colorblind-Friendly:**
```css
body.colorblind-mode {
  --primary: #4477aa;      /* Blue instead of teal */
  --secondary: #009e73;    /* Bluish-green */
}
```

**High Contrast:**
```css
body.high-contrast {
  --bg: #ffffff;
  --primary: #000000;
  --text: #000000;
  --shadow: none;
}
```

**Text Sizes:**
```css
body.text-normal { font-size: 16px; }
body.text-large { font-size: 18px; }
body.text-xl { font-size: 20px; }
```

---

## JavaScript Modules

### 1. `accessibility.js`

**Purpose:** Manages accessibility settings with localStorage persistence.

**Features:**
- Text size toggle (Normal / Large / XL)
- Colorblind mode toggle
- High contrast mode toggle
- Reset all settings
- Keyboard navigation (Escape closes menu)

**Storage Keys:**
```javascript
localStorage.getItem("textSize")        // "text-normal" | "text-large" | "text-xl"
localStorage.getItem("colorblindMode")  // "0" | "1"
localStorage.getItem("highContrast")    // "0" | "1"
```

---

### 2. `firebase-placeholder.js`

**Purpose:** Mock authentication placeholder.

```javascript
function mockAuthLogin(email, password) {
  console.log("Mock auth login", { email, password });
  return true;  // Always succeeds
}
```

**Future:** Replace with Firebase Auth SDK initialization.

---

### 3. `visualization.js`

**Purpose:** Chart.js helpers for the dashboard.

**Key Class:** `MentalHealthVisualization`

**Methods:**
| Method | Description |
|--------|-------------|
| `createRadarChart(canvasId, scores)` | Spider chart comparing all 4 scores |
| `createBarChart(canvasId, scores)` | Vertical bar chart |
| `createTrendChart(canvasId, history)` | Line chart over time |
| `createGauge(canvasId, scoreType, value)` | Semi-circle gauge with severity |
| `createComparisonChart(canvasId, current, previous)` | Before/after comparison |

**API Helpers:**
```javascript
await fetchPrediction(answers, freeText, userId)  // POST /api/v2/predict
await fetchHistory(userId, limit)                  // GET /api/v2/history
await fetchMetrics(userId)                         // GET /api/v2/metrics
await checkApiStatus()                             // GET /api/v2/status
await renderDashboard(containerId, userId)         // Full dashboard render
```

**Color Palette:**
```javascript
COLORS = {
  stress: { main: 'rgba(239, 154, 154, 1)', light: '...' },     // Soft red
  depression: { main: 'rgba(149, 117, 205, 1)', ... },           // Soft purple
  anxiety: { main: 'rgba(129, 199, 132, 1)', ... },              // Soft green
  sleep: { main: 'rgba(100, 181, 246, 1)', ... },                // Soft blue
}
```

---

## User Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Landing Page (/)                       │
│  • Hero with animated title                                 │
│  • "Start now" → /login                                     │
│  • "Take a survey" → /survey                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Login (/login)                         │
│  • Email + Password form                                    │
│  • Mock auth (any credentials work)                         │
│  • On success → /dashboard                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Dashboard (/dashboard)                    │
│  • Welcome message with email                               │
│  • Survey history list                                      │
│  • "Take Survey" button                                     │
│  • (Future: Trend charts, gauges)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Survey (/survey)                        │
│  • 24 Yes/No questions from schema.json                     │
│  • Submit → /survey-submit                                  │
│  • Runs ML inference                                        │
│  • Stores result in history                                 │
│  • Redirect back to dashboard                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Backend Routes (Frontend Blueprint)

| Route | Method | Handler | Description |
|-------|--------|---------|-------------|
| `/login` | GET | `login()` | Show login form |
| `/login` | POST | `login()` | Process login, set session |
| `/dashboard` | GET | `dashboard()` | Show user dashboard |
| `/survey` | GET | `survey()` | Show survey questions |
| `/survey-submit` | POST | `survey_submit()` | Process survey, run inference |

**Session Data:**
```python
session["user_email"]  # Logged-in user's email
```

**In-Memory Store:**
```python
USER_STORE = {
    "user@example.com": {
        "last_login": "2025-12-05T...",
        "history": [
            {"timestamp": "...", "prediction": "Anxiety", "confidence": 0.85}
        ]
    }
}
```

---

## Animations

### Splash Screen

1. **First Load:**
   - Opaque purple background
   - Four-line box animation around "WALLS"
   - Catchphrase visible
   - Click logo to dismiss

2. **Repeat Loads:**
   - Semi-transparent background
   - No catchphrase
   - Auto-dismiss after 3.2 seconds

### Title Animation

Titles with `data-animate="chars"` are split into individual `<span>` elements:

```css
.fade-chars span {
  opacity: 0;
  animation: fadeCharIn 0.4s ease forwards;
  animation-delay: calc(var(--i) * 0.04s);
}
```

### Content Fade-In

```css
.fade-in { animation: fadeIn 0.5s ease-out; }
.fade-delayed { animation: fadeIn 0.6s ease-out 0.2s both; }
```

---

## Future Enhancements

1. **Real Firebase Auth** — Replace mock login with Firebase SDK
2. **Dashboard Visualizations** — Integrate `visualization.js` charts
3. **Persistent Storage** — Move from in-memory to database/Firestore
4. **Free Text Input** — Add textarea for TF-IDF sentiment analysis
5. **Score Display** — Show stress/depression/anxiety/sleep scores
6. **Trend Charts** — Line graphs of score history
7. **User Profiles** — Store preferences and settings

---

## Quick Reference

### To Add a New Page

1. Create `templates/newpage.html`:
   ```html
   {% extends "base.html" %}
   {% block title %}New Page{% endblock %}
   {% block content %}
     <section class="hero fade-in">
       <h1 data-animate="chars">Page Title</h1>
     </section>
   {% endblock %}
   ```

2. Add route in `frontend/routes.py`:
   ```python
   @frontend_bp.get("/newpage")
   def newpage():
       return render_template("newpage.html")
   ```

### To Add Visualization

```html
<canvas id="my-chart"></canvas>
<script src="{{ url_for('static', filename='js/visualization.js') }}"></script>
<script>
  const viz = new MentalHealthVisualization();
  viz.createRadarChart('my-chart', {
    stress_score: 15,
    depression_score: 8,
    anxiety_score: 12,
    sleep_quality: 3
  });
</script>
```

---

## Files to Modify

| To Change | Edit |
|-----------|------|
| Global styles | `Static/css/styles.css` |
| Page layout | `templates/base.html` |
| Individual page | `templates/<page>.html` |
| Routes/logic | `frontend/routes.py` |
| Accessibility | `Static/js/accessibility.js` |
| Charts | `Static/js/visualization.js` |
| Auth (future) | `Static/js/firebase-placeholder.js` |

