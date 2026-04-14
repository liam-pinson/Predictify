# Architecture

## System Architecture Diagram

```mermaid
flowchart TD
    User(["👤 User (Browser)"])

    subgraph Frontend ["🖥️ Frontend"]
        NX["Next.js\nFrontend Framework"]
        TW["Tailwind CSS\nStyling"]
    end

    subgraph Backend ["⚙️ Backend"]
        FA["FastAPI\nBackend API"]
    end

    subgraph ML ["🧠 ML & Processing"]
        PT["PyTorch\nML Model"]
        LB["Librosa\nAudio Feature Extraction"]
        SD["spotDL\nAudio Downloader"]
        GM["Google Gemini AI\nLLM Producer Insight"]
    end

    subgraph ExternalAPI ["🎵 External API"]
        SP["Spotify API\nTrack Metadata"]
    end

    subgraph CICD ["🚀 CI/CD & Infrastructure"]
        direction LR
        GL["GitLab / GitHub\nVersion Control & CI/CD"]
        DK["Docker\nContainerization"]
        GCP["Google Cloud Platform\nCloud Services"]
        GKE["Google Kubernetes Engine\nContainer Orchestration"]
        GL --> DK --> GCP --> GKE
    end

    User --> NX
    NX --> FA
    FA --> PT
    FA --> LB
    FA --> SD
    FA --> GM
    FA --> SP
    PT --> NX
    LB --> NX
    GM --> NX
    SP --> NX
    GKE -->|"Serves"| FA
```

## Layer Overview

| Layer | Technology | Role |
|---|---|---|
| Frontend | Next.js | UI & search interface |
| Frontend | Tailwind CSS | Styling |
| Backend | FastAPI | API server & orchestration |
| ML | PyTorch | Hit prediction model |
| ML | Librosa | Audio feature extraction |
| ML | spotDL | Audio downloading |
| AI | Google Gemini AI | LLM producer insights |
| External API | Spotify API | Track metadata |
| CI/CD | GitLab / GitHub | Version control & pipelines |
| DevOps | Docker | Containerization |
| Cloud | Google Cloud Platform | Cloud infrastructure |
| Orchestration | Google Kubernetes Engine | Container deployment |
