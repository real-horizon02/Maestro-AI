#!/bin/bash

# Start Celery worker in background with concurrency=2 to conserve memory
echo "Starting Celery worker in background..."
celery -A workers.celery_worker.celery_app worker --loglevel=info --concurrency=2 -Q retriever_queue,analyzer_queue,writer_queue,validator_queue &

# Start FastAPI server in foreground
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
