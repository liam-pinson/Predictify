#!/bin/bash
PROJECT_ID=your_gcp_project_id
IMAGE_NAME=spotify-hit-predictor

docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME
echo "Image pushed to GCR"
