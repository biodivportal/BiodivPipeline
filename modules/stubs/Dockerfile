FROM python:3.11-slim
RUN pip install fastapi uvicorn
COPY stub_service.py /app/stub_service.py
WORKDIR /app
CMD ["uvicorn", "stub_service:app", "--host", "0.0.0.0", "--port", "8000"]
