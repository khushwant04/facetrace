.PHONY: backend run clean

backend:
	. .venv/bin/activate && cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	make backend

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete