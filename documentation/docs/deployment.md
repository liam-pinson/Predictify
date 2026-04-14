# Deployment

## CI/CD Pipeline

1. Push code to GitLab / GitHub
2. CI/CD pipeline triggers Docker build
3. Image pushed to Google Container Registry (GCR)
4. GKE pulls and deploys the updated image

## Docker

```bash
docker build -t spotify-hit-predictor .
docker push gcr.io/YOUR_PROJECT/spotify-hit-predictor
```

## GKE

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Environment Variables

Set in GKE secrets or `.env`:

```
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
GEMINI_API_KEY=
```
