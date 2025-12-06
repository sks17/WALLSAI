# Architecture Report (PyTorch Mental-Health App)

## 1. Directory Structure
- `app.py`: Flask entrypoint; registers `api`, `frontend`, and `legacy` blueprints. Uses `Static/` for assets and `templates/` for rendering.
- `api/`: JSON API layer.
  - `routes.py`: Blueprint `api` exposing `/api/ping` and `/api/predict`.
  - `predict.py`: Loads `ml/model.pt` + `ml/metadata.json` and runs inference.
- `ml/`: PyTorch pipeline.
  - `model.py`: MLP definition and `from_pretrained`.
  - `preprocess.py`: Encodes yes/no answers, batch preprocessing.
  - `train.py`: Training script; saves `model.pt` and `metadata.json`.
  - `explain.py`: Stub for interpretability.
- `data/`: Data utilities.
  - `schema.json`: Feature/label schema.
  - `loader.py`, `__init__.py`: CSV loading and schema loading.
- `Static/`: Frontend assets.
  - `css/styles.css`, `js/firebase-placeholder.js`, `Data/dataset.csv`, images, `junk.csv`.
- `templates/`: Flask HTML templates.
  - Legacy pages (`main.html`, `home.html`, etc.), modern pages (`login.html`, `dashboard.html`, `survey.html`, `index.html`, `signup.html`).
- `frontend/`: Modern UI blueprint.
  - `routes.py`: Login, dashboard, survey flow; uses session + in-memory history.
- `legacy/`: Preserved legacy app.
  - `web.py`: Legacy routes (including `/login`, `/survey`, `/process-data`).
  - `disorder.py`: Legacy DecisionTree training on every request.
- `colorama/`: Local stub to shadow broken global colorama.
- `dashboard/placeholder.txt`, `TSA_Project/`: placeholder/unused static copies.
- Root files: `requirements.txt`, `README.md`, `package*.json` (frontend libs), `styles.css` (unused top-level duplicate), `get-pip.py`, `Info.md`.

## 2. ML Pipeline Analysis
- Training (`ml/train.py`):
  - Loads CSV from `Static/Data/dataset.csv`.
  - Loads schema via `data.load_schema()` (features/labels from `data/schema.json`).
  - `Preprocessor.preprocess_batch` converts yes/no strings to float tensors and encodes labels to indices.
  - Splits train/val, trains MLP (input 24 → hidden [64,32,16] → 5 outputs), saves `ml/model.pt` and `ml/metadata.json` (with schema, label map, version, config; paths stored relative).
- Inference (`api/predict.py`):
  - Lazy-caches metadata and model; uses `ModelConfig` from metadata.
  - `Preprocessor.encode_answers` converts 24 answers to tensor (1,24).
  - `model.predict_proba` → softmax; returns prediction, confidence, probabilities, model_version.
- Metadata/model usage:
  - `metadata.json` drives label list, feature order, label-to-idx map, and config for model reconstruction.
  - `model.pt` stores state_dict loaded on CPU.
- Schema:
  - `data/schema.json` enumerates 24 feature names and 5 labels; used by preprocessing, survey rendering, and metadata generation.

## 3. Flask Application Architecture
- Blueprint registration (`app.py`): `api` (url_prefix `/api`), `frontend` (no prefix), `legacy` (no prefix). Order: api → frontend → legacy.
- Blueprint names/endpoints:
  - `api`: endpoints `api.ping`, `api.predict`.
  - `frontend`: endpoints `frontend.login`, `frontend.dashboard`, `frontend.survey`, `frontend.survey_submit`.
  - `legacy`: endpoints `legacy.home`, `legacy.login`, `legacy.survey`, `legacy.process_data`, etc.
- Routing flow:
  - Root `/` served by `legacy.home` rendering `index.html` (from legacy blueprint).
  - Modern entry: `/login` (frontend) → sets session and redirects to `/dashboard`.
  - Survey flow (frontend): `/survey` → `/survey-submit` → dashboard.
  - Legacy routes coexist (also define `/login`); namespace separation relies on blueprint names; no URL prefix differences, so first-registered blueprint claims the URL.
- Conflicts/duplicates:
  - `/login` exists in both `frontend` and `legacy`; because `frontend` registers before `legacy`, `/login` resolves to `frontend.login`. Legacy’s `/login` is unused unless blueprints reordered. No BuildError now because templates target `frontend.login`.

## 4. Frontend UI Path
- Modern templates:
  - `templates/login.html`: posts to `frontend.login` (same endpoint for GET/POST); mock JS login.
  - `templates/dashboard.html`: shows `user_email`, history, link to `frontend.survey`.
  - `templates/survey.html`: renders questions from `features` passed by frontend route; posts to `frontend.survey_submit`.
  - `templates/index.html`: landing; Login button uses `url_for('frontend.login')`; Register still points to `url_for('register')` (legacy register route).
  - `templates/signup.html`: links now use `frontend.login`.
- Legacy templates (e.g., `main.html`, `home.html`) still use legacy flow.
- Script-based redirects: `index.html` uses `window.location.href = "{{ url_for('frontend.login') }}"`; `signup.html` uses the same; no remaining `url_for('login')` references.

## 5. Import Paths
- Local package imports:
  - `api.predict` imports from `ml.model`, `ml.preprocess`.
  - `frontend.routes` imports `api.predict.run_inference`, `data.load_schema`.
  - `ml.train` imports `data.load_schema`, `data.loader.load_csv`, `ml.model`, `ml.preprocess`.
  - `legacy.web` imports `legacy.disorder`.
  - `legacy.disorder` imports pandas/sklearn directly (no package import issues).
  - `app.py` imports `api`, `frontend`, `legacy`.
- `__init__.py` presence: exists in `api/`, `ml/`, `data/`, `frontend/`, `legacy/`, `colorama/`.
- Potential sys.path issues:
  - Running `python ml/train.py` from project root works because imports are relative to package and root is on sys.path. Running from outside root without `PYTHONPATH` could trigger `ModuleNotFoundError: data`. Ensure execution from repo root or adjust PYTHONPATH if needed.

## 6. Root Causes
- `ModuleNotFoundError: No module named 'data'`:
  - Occurs if `ml/train.py` is run with CWD not at project root, so the `data` package is not on sys.path. Solution: run from repo root or add root to PYTHONPATH. Packages themselves are correctly structured.
- BuildError: Could not build url for endpoint 'login':
  - Caused by templates referencing `url_for('login')` while only `frontend.login`/`legacy.login` endpoints exist (namespaced by blueprint). Fixed by updating templates to `url_for('frontend.login')`. Also, `frontend` blueprint is registered before `legacy`, so `/login` resolves to `frontend.login`.

## NEXT ACTIONS NEEDED
- Enforce running training/scripts from repo root or document PYTHONPATH usage to avoid `ModuleNotFoundError: data`.
- Audit legacy template links (e.g., `index.html` register button still points to legacy `register`) and decide desired flow.
- Consider adding url_prefix to legacy blueprint to eliminate route collisions with frontend (optional).
- Add automated check or note to ensure `ml/metadata.json` and `ml/model.pt` exist before serving `/api/predict`.

