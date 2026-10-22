# Backend

## Setup with uv (recommended)

```
cd src/backend
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
cp .env.example .env   # fill in values
uv run fastapi dev app/main.py
```

`uv run` uses the `.venv` automatically, so activating it is optional.

## Setup with pip

```
cd src/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
fastapi dev app/main.py
```

Docs: http://localhost:8000/docs
