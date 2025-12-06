# TSA-Software-Development

## Local Setup (Python 3.14 / Windows)

This project includes a local `colorama` stub to avoid known ctypes/Windows issues with Python 3.14. No global Python packages are required.

1) Create and activate a virtual environment (PowerShell):
```
python -m venv .venv
.\\.venv\\Scripts\\activate
```

2) Install dependencies:
```
pip install -r requirements.txt
```

# All runtime ML (PyTorch + sklearn + sentence-transformers) is included and
# runs on Vercel Enhanced Builds. For local experimentation you can also:
# pip install -r requirements-dev.txt

3) Train the model (optional, uses local CSV):
```
python ml/train.py
```

4) Run the app:
```
python app.py
```
Visit http://localhost:5000/login

Production deployment uses a slim dependency set to avoid serverless build
memory limits. Heavy ML tooling (pandas/scikit-learn/transformers, etc.) lives
in `requirements-dev.txt` for training and experimentation.

The repo-local `colorama` stub ensures Flask/Werkzeug run even if system colorama is broken. Vercel deployment remains unaffected.