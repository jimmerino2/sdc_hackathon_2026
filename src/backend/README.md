# Backend

```
cd src/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
fastapi dev app/main.py
```

Docs: http://localhost:8000/docs
