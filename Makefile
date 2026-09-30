.PHONY: run test

run:
	python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000

test:
	python -m pytest backend/tests -v
