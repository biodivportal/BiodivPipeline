.PHONY: format lint lint-fix test install docker run stop clear

IMAGE_NAME = column_standardizer
CONTAINER_NAME = column_standardizer-container

format:
	ruff format .

lint:
	ruff check .

lint-fix:
	ruff check . --fix

test:
	PYTHONPATH=. pytest tests/

install:
	pip install -r requirements.txt

docker:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -d -p 8000:8000 -v "$(PWD)/data:/app/data" --name $(CONTAINER_NAME) $(IMAGE_NAME)
	@echo "Container is running at http://localhost:8000"

stop:
	docker stop $(CONTAINER_NAME)
	docker rm $(CONTAINER_NAME)
	@echo "Container stopped and removed."

clear:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	@echo "Cache data cleared."
