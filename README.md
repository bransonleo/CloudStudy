# CloudStudy: AI-Powered Study Assistant

> Singapore Institute of Technology  
> CSD3156 Mobile and Cloud Computing  
> AY 2025/2026, Trimester 2  
> Cloud Computing Project Team 10

CloudStudy is a cloud-based web application that allows students to upload study materials (PDFs, images, or text) and automatically generates summaries, quiz questions, flashcards, and translations using AI.

Built on AWS with an N-tier architecture designed for scalability, reliability, elasticity, and security.

## Architecture

```
Users (Browser)
      │
      ▼
┌─────────────┐
│ Frontend UI │  React (Vite) / HTML+JS
└──────┬──────┘
       │ HTTPS
       ▼
┌──────────────────────┐
│ Application Load     │  Routes traffic, health checks
│ Balancer (ALB)       │
└──────┬───────────────┘
       │
┌──────▼───────────────┐
│ Auto-Scaling Group   │
│ ┌────────┐ ┌────────┐│
│ │EC2     │ │EC2     ││  Python Flask (gunicorn)
│ │Backend │ │Backend ││  t2.micro instances
│ └───┬────┘ └───┬────┘│
└─────┼──────────┼─────┘
      │          │
  ┌───▼───┐ ┌────▼───┐ ┌──────────┐ ┌───────────┐
  │  S3   │ │  RDS   │ │ Gemini   │ │ Textract/ │
  │(files)│ │(MySQL) │ │ API (AI) │ │ Translate │
  └───────┘ └────────┘ └──────────┘ └───────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) |
| Backend | Python 3.11+, Flask, gunicorn |
| Database | Amazon RDS (MySQL) |
| File Storage | Amazon S3 |
| AI / LLM | Google Gemini API (gemini-2.5-flash) |
| OCR | Amazon Textract |
| Translation | Amazon Translate |
| Authentication | Amazon Cognito |
| Infrastructure | VPC, ALB, Auto-Scaling Group, EC2 |

## Features

- Upload study materials (PDF, images, plain text)
- AI-generated summaries of study content
- Auto-generated multiple-choice quiz questions
- Flashcard generation for revision
- Multi-language translation of study materials
- User authentication via Cognito JWT (RS256)
- Horizontally scalable backend with auto-scaling

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- AWS CLI v2 (configured with Learner Lab credentials)
- Google Gemini API key ([get one here](https://aistudio.google.com/))

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # Then fill in your keys
python run.py
```

The backend runs at `http://localhost:5000`. Test with:

```bash
curl http://localhost:5000/api/health
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Project Structure

```
CloudStudy/
├── backend/                      # Flask API server
│   ├── app/
│   │   ├── __init__.py           # App factory, CORS, auth middleware, blueprints, error handlers
│   │   ├── config.py             # Configuration (reads from .env)
│   │   ├── pipeline.py           # Upload orchestration and AI generation pipeline
│   │   ├── routes/               # API endpoint blueprints
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── upload.py         # POST /api/upload
│   │   │   ├── generate.py       # POST /api/generate/<material_id>
│   │   │   └── results.py        # GET /api/results/<material_id>
│   │   ├── middleware/           # Auth middleware
│   │   │   ├── __init__.py
│   │   │   └── auth.py           # before_request hook, @require_auth decorator
│   │   └── services/             # AWS and AI service wrappers
│   │       ├── auth_service.py   # Cognito JWKS fetching and JWT verification
│   │       ├── db_service.py     # RDS MySQL CRUD
│   │       ├── s3_service.py     # S3 file upload and retrieval
│   │       ├── ocr_service.py    # Text extraction (Textract + pdfplumber)
│   │       └── ai_service.py     # Gemini AI generation
│   ├── tests/                    # Pytest test suite (70 tests)
│   │   ├── conftest.py           # Shared fixtures
│   │   ├── test_health.py
│   │   ├── test_upload.py
│   │   ├── test_services.py
│   │   ├── test_pipeline.py
│   │   ├── test_generate.py
│   │   ├── test_results.py
│   │   ├── test_auth.py          # Auth service and middleware tests
│   │   └── test_user_scoping.py  # User data isolation tests
│   ├── requirements.txt          # Python runtime dependencies
│   ├── requirements-dev.txt      # Dev/test dependencies
│   ├── .env.example              # Environment variable template
│   └── run.py                    # Entry point
├── frontend/                     # React app (Vite)
└── docs/                         # Project documentation
```

## API Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/api/health` | ✅ Live | Health check: returns `{"status": "ok"}` |
| POST | `/api/upload` | ✅ Live | Upload a study material; starts background OCR |
| POST | `/api/generate/<material_id>` | ✅ Live | Generate summary, quiz, or flashcards |
| GET | `/api/results/<material_id>` | ✅ Live | Retrieve material status and generated content |

All endpoints except `/api/health` require `Authorization: Bearer <token>`. Tokens are issued by Cognito via the frontend login flow.

See [docs/api-contract.md](docs/api-contract.md) for request/response details.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values. See the template for all required variables. **Never commit `.env` files.**

## Team

| Name | Role | Student ID |
|------|------|------------|
| Leo Yew Siang, Branson | Backend & AI Engineer | 2301321 |
| Chiu Jun Jie | Technical PM | 2301524 |
| Chua Sheng Kai Jovan | Frontend Developer | 2301244 |
| Cheong Jia Zen | Data & Security Engineer | 2301549 |

## Acknowledgements

Developed for CSD3156 Mobile and Cloud Computing, Singapore Institute of Technology.
