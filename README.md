# CloudStudy: AI-Powered Study Assistant

> Singapore Institute of Technology  
> CSD3156 Mobile and Cloud Computing  
> AY 2025/2026, Trimester 2  
> Cloud Computing Project Team 10

CloudStudy is a cloud-based web application that allows students to upload study materials (PDFs, images, or text) and automatically generates summaries, quiz questions, and flashcards using AI.

Built on AWS with an N-tier architecture designed for scalability, reliability, elasticity, and security.

## Architecture

```
Users (Browser)
      │
      ▼
┌─────────────┐
│ Frontend UI │  React (Vite) / HTML+JS
└──────┬──────┘
       │ HTTPS (443)
       ▼
┌──────────────────────┐
│ Application Load     │  HTTPS termination, routes traffic
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
  ┌───▼───┐ ┌────▼───┐ ┌──────────┐ ┌──────────┐
  │  S3   │ │  RDS   │ │ Gemini   │ │ Textract │
  │(files)│ │(MySQL) │ │ API (AI) │ │  (OCR)   │
  └───────┘ └────────┘ └──────────┘ └──────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) + TypeScript |
| Backend | Python 3.11+, Flask, gunicorn |
| Database | Amazon RDS (MySQL) |
| File Storage | Amazon S3 |
| AI / LLM | Google Gemini API (gemini-2.5-flash) |
| OCR | Amazon Textract |
| Authentication | Amazon Cognito (Hosted UI + TOTP MFA) |
| Infrastructure | CloudFormation, VPC, ALB, Auto-Scaling Group, EC2 |

## Features

- Upload study materials (PDF, images, plain text)
- AI-generated summaries of study content
- Auto-generated multiple-choice quiz questions
- Flashcard generation for revision
- User authentication via Cognito (JWT RS256 + TOTP MFA)
- Horizontally scalable backend with auto-scaling

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20.19+ and npm
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

### Infrastructure Deployment

See [infra/README.md](infra/README.md) for full details. A single script handles the entire deployment including HTTPS setup and Cognito configuration:

```bash
# Export Learner Lab credentials first, then:
bash infra/deploy.sh <rds-password> <gemini-api-key>
```

Teardown:

```bash
bash infra/teardown.sh
```

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
├── frontend/                     # React + TypeScript (Vite)
│   └── src/
│       ├── api/                  # Fetch client, Cognito helpers, mock data
│       ├── components/           # Navbar, FileDropZone, FlashCard, QuizQuestion, ProtectedRoute
│       ├── context/              # AuthContext (Cognito session state)
│       ├── pages/                # Login, Callback, Dashboard, Upload, Result, History, TwoFactor, ApiKey
│       └── types/                # Shared TypeScript interfaces
├── infra/                        # AWS deployment
│   ├── network.yaml              # VPC, subnets, IGW, NAT GW, route tables, security groups
│   ├── app.yaml                  # ALB, ASG, Launch Template, CloudWatch alarms
│   ├── deploy.sh                 # One-command deploy (stacks + HTTPS + Cognito + frontend)
│   └── teardown.sh               # Ordered stack teardown
└── docs/                         # Project documentation
    ├── api-contract.md           # Full API endpoint reference
    └── project-proposal.md       # CSD3156 project proposal (submitted Week 11)
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
