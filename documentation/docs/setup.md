# Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- Spotify Developer Account
- Google Gemini API Key
- Docker (for deployment)

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
GEMINI_API_KEY=your_gemini_key
```
