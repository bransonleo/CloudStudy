# CloudStudy Backend

AI-powered study assistant backend that processes uploaded study materials (PDFs, images, Word documents, text files) and generates summaries, quiz questions, and flashcards using Google Gemini.

Built for the **CSD3156 Mobile and Cloud Computing** module. Deployed on AWS with a fully cloud-native architecture.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Project Structure](#project-structure)
3. [Tech Stack](#tech-stack)
4. [Core Features and Backend Logic](#core-features-and-backend-logic)
5. [Design Tradeoffs and Known Limitations](#design-tradeoffs-and-known-limitations)
6. [API Design](#api-design)
7. [AWS Architecture](#aws-architecture)
8. [Database Schema and Data Modeling](#database-schema-and-data-modeling)
9. [Security](#security)
10. [Development Workflow](#development-workflow)
11. [Future Improvements](#future-improvements)

---

## System Architecture

The backend follows a **layered service-oriented architecture**: a deliberate monolith with clean separation between layers.

### Request Lifecycle

```
Client Request
      |
      v
  ALB (HTTPS)
      |
      v
  gunicorn (WSGI)
      |
      v
  Flask App Factory         # app/__init__.py - CORS, error handlers, blueprint registration
      |
      v
  Auth Middleware           # middleware/auth.py - JWT verification (before_request hook)
      |
      v
  Blueprint Routes          # routes/ - input validation, HTTP semantics
      |
      v
  Pipeline Orchestrator     # pipeline.py - multi-step workflow coordination
      |
      v
  Service Layer             # services/ - one module per external dependency
      |
      v
  AWS / External APIs       # S3, RDS, Textract, Cognito, Gemini
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| **Middleware** | `middleware/auth.py` | JWT extraction, Cognito token verification, user identity injection into Flask `g` |
| **Routes** | `routes/` (4 Blueprints) | Request parsing, input validation, HTTP status code semantics, error response formatting |
| **Orchestration** | `pipeline.py` | Coordinates multi-step workflows (upload + background OCR, text retrieval + AI generation) |
| **Services** | `services/` (5 modules) | Each wraps exactly one external dependency with a clean internal API |

### Application Factory Pattern

The app is constructed via `create_app()` in `app/__init__.py`, which:

1. Loads configuration from environment variables (`config.py`)
2. Enables CORS for the frontend origin
3. Registers the auth middleware (`before_request` hook)
4. Registers 4 Flask Blueprints under the `/api/` prefix
5. Creates database tables on startup (skipped in test mode)
6. Installs global error handlers (404, 413, 500) with consistent JSON responses

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py            # App factory: CORS, auth middleware, blueprints, error handlers
│   ├── config.py              # Configuration loaded from environment variables
│   ├── pipeline.py            # Orchestrator: upload jobs, background OCR, AI generation
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py            # before_request hook + @require_auth decorator
│   ├── routes/
│   │   ├── health.py          # GET  /api/health
│   │   ├── upload.py          # POST /api/upload
│   │   ├── generate.py        # POST /api/generate/<material_id>
│   │   └── results.py         # GET  /api/results/<material_id>
│   └── services/
│       ├── auth_service.py    # Cognito JWKS fetch + RS256 JWT verification
│       ├── db_service.py      # PyMySQL CRUD for materials and results tables
│       ├── s3_service.py      # boto3 S3 upload and download
│       ├── ocr_service.py     # Text extraction (Textract, pdfplumber, python-docx)
│       └── ai_service.py      # Gemini prompt construction + JSON response parsing
├── tests/
│   ├── conftest.py            # Shared fixtures (Flask test client)
│   ├── test_health.py         # Health endpoint tests
│   ├── test_upload.py         # Upload route tests
│   ├── test_generate.py       # Generate route tests
│   ├── test_results.py        # Results route tests
│   ├── test_services.py       # Unit tests for all service modules
│   ├── test_pipeline.py       # Pipeline orchestrator tests
│   ├── test_auth.py           # Auth service + middleware tests
│   └── test_user_scoping.py   # Cross-tenant data isolation tests
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Dev/test dependencies (pytest)
├── .env.example               # Environment variable template
└── run.py                     # Application entry point
```

---

## Tech Stack

| Technology | Why Chosen |
|---|---|
| **Flask** | Lightweight and minimal for a REST API backend. No ORM or template engine overhead. The application factory pattern provides clean initialization and testability. |
| **PyMySQL (raw SQL)** | Direct control over queries. The schema has only 2 tables, so an ORM adds abstraction without proportional benefit. Keeps memory usage low on t2.micro instances. |
| **google-genai SDK** | Official Google SDK for the Gemini API. The free tier (10 RPM, 250 RPD) is sufficient for a student project. `gemini-2.5-flash` provides fast, structured JSON responses. |
| **pdfplumber** | Pure Python PDF text extraction with no native C dependencies. Easy to install on EC2 without system-level packages. More accurate table/layout extraction than alternatives. |
| **Amazon Textract** | Cloud-native OCR for image files (PNG, JPG). Eliminates the need to install and run ML models on resource-constrained t2.micro instances. |
| **Amazon Cognito** | Fully managed authentication with hosted UI, JWT issuance, and TOTP MFA support. No custom auth server or password storage required. |
| **gunicorn** | Production-grade WSGI server. Pre-fork worker model handles concurrent requests without the complexity of async. |
| **boto3** | Official AWS SDK with built-in retry logic, credential chain, and consistent interface across S3, Textract, and other services. |

---

## Core Features and Backend Logic

### Asynchronous Upload Pipeline

The upload flow is the most architecturally significant feature. It uses a **non-blocking pattern** where the API returns immediately while text extraction runs in the background.

**How it works** (`pipeline.py`):

1. `POST /api/upload` receives a multipart file
2. `start_upload_job()` uploads the file to S3, creates a database record with status `extracting`, and spawns a background thread
3. The endpoint returns **HTTP 202 Accepted** with the `material_id` immediately
4. The background thread (`_run_ocr`) downloads the file from S3, extracts text, and updates the database status to `ready` or `error`

```
POST /api/upload
      |
      +---> S3: upload file
      +---> RDS: INSERT material (status='extracting')
      +---> Thread: _run_ocr(material_id)
      |           |
      |           +---> S3: download file bytes
      |           +---> OCR: extract text (Textract / pdfplumber / python-docx / UTF-8)
      |           +---> RDS: UPDATE material (status='ready', extracted_text=...)
      |
      +---> Return 202 {"material_id": "...", "status": "extracting"}
```

The thread receives its own Flask application context via `with app.app_context()` to access configuration and database connections.

**State machine:**

```
extracting  --(success)-->  ready
extracting  --(failure)-->  error
```

### Multi-Format Text Extraction

The OCR service (`services/ocr_service.py`) routes files to the appropriate extraction strategy based on content type, with file extension as a fallback for ambiguous MIME types (e.g., `application/octet-stream`):

| File Type | Extraction Method | Library |
|---|---|---|
| PDF | Page-by-page text extraction | pdfplumber |
| PNG / JPG / JPEG | Cloud OCR via AWS | Amazon Textract |
| DOCX | Paragraph extraction | python-docx |
| TXT / MD | Direct UTF-8 decode | Built-in |

This hybrid approach uses **cloud OCR only where necessary** (images), falling back to lighter local libraries for structured formats (PDF, Word) to minimize AWS API costs.

### AI Content Generation

The generation pipeline (`services/ai_service.py`) supports three output types, each with a carefully crafted prompt that enforces structured JSON output:

| Type | Output Structure | Prompt Strategy |
|---|---|---|
| **Summary** | `{title, key_points[], summary}` | Requests structured breakdown with key points |
| **Quiz** | `{questions[{question, options[], correct_index, explanation}]}` | Generates multiple-choice with explanations; supports `format_hint` for custom question count |
| **Flashcards** | `{flashcards[{front, back}]}` | Generates comprehensive coverage of all key concepts |

**Key implementation details:**

- **Markdown fence stripping:** Gemini sometimes wraps JSON in ` ```json ``` ` code blocks despite explicit instructions. The service strips these fences before parsing (`ai_service.py`).
- **Upsert pattern:** Re-generating the same type for a material overwrites the previous result rather than creating duplicates (`db_service.py`).
- **Per-request API key:** Users can supply their own Gemini API key via the `X-Gemini-Api-Key` header, allowing the system to function without a server-side key.
- **Format hints:** The `format_hint` parameter allows the frontend to customize generation (e.g., specifying the number of quiz questions).

### Pipeline Error Handling

The pipeline defines a custom exception hierarchy that maps directly to HTTP semantics:

| Exception | HTTP Status | Meaning |
|---|---|---|
| `MaterialNotFound` | 404 | Material ID does not exist or belongs to another user |
| `MaterialNotReady` | 409 Conflict | OCR is still running; client should retry |
| `MaterialFailed` | 422 Unprocessable | Text extraction failed permanently |

Generation errors are **persisted to the database** before being re-raised, ensuring that failed attempts are recorded for debugging (`pipeline.py`).

---

## Design Tradeoffs and Known Limitations

These tradeoffs reflect deliberate decisions made within the constraints of the AWS Learner Lab ($50 budget, LabRole IAM, t2.micro instances) and the Gemini free tier.

### Threading vs Task Queue

Background OCR uses Python's `threading.Thread` rather than a task queue like Celery. Celery requires a message broker (SQS or Redis), which adds infrastructure complexity and ongoing cost. For a student project with low concurrency, threading provides adequate reliability without additional services.

The tradeoff is that daemon threads have no retry mechanism and no dead-letter queue. If the gunicorn worker process restarts while OCR is running, the affected material remains in `extracting` status permanently. At the expected scale of a class project, this is an acceptable constraint.

### No Connection Pooling

Each database call in `db_service.py` opens and closes a new TCP connection via PyMySQL. This avoids the complexity of managing a connection pool, which is justified by the simple 2-table schema and low expected concurrency. The Learner Lab's db.t3.micro instance supports roughly 66 simultaneous connections, which is adequate for the expected user base.

### Gemini Free Tier Constraints

The Gemini API free tier allows 10 requests per minute and 250 per day. The backend does not enforce server-side rate limiting because the expected usage falls well within these limits. As additional mitigation, the `X-Gemini-Api-Key` header allows users to supply their own API key, distributing usage across multiple keys.

### Synchronous Generation

Gemini API calls in `ai_service.py` block the gunicorn worker synchronously with no explicit timeout. At the expected scale of a class demonstration, worker exhaustion is unlikely. A higher-concurrency deployment would benefit from async workers or a task queue for generation.

### CORS Configuration

`CORS(app)` is called with no origin restrictions, allowing requests from any domain. In the Learner Lab environment, the ALB DNS name changes with each redeployment, making it impractical to hardcode a specific frontend origin. See the [Security](#security) section for further detail.

---

## API Design

All endpoints are prefixed with `/api/` and follow REST conventions. Every error response uses a consistent JSON format:

```json
{"error": "Human-readable message", "status": 4xx}
```

### Endpoints

| Method | Endpoint | Auth | Description | Response |
|---|---|---|---|---|
| `GET` | `/api/health` | No | ALB health check | `200 {"status": "ok"}` |
| `POST` | `/api/upload` | Yes | Upload file, start OCR | `202 {"material_id": "...", "status": "extracting"}` |
| `POST` | `/api/generate/<material_id>` | Yes | Generate AI content | `200 {result_id, material_id, type, content}` |
| `GET` | `/api/results/<material_id>` | Yes | Fetch material + results | `200 {material_id, filename, status, results{...}}` |

### Design Decisions

- **POST for generation** (not GET): Generation triggers a side effect (Gemini API call + database write), so POST is semantically correct despite returning data.
- **202 for upload**: The response confirms acceptance, not completion. The client polls `/api/results/<material_id>` to check when OCR finishes.
- **Consistent error format**: All error responses include both a human-readable `error` string and a numeric `status` code, simplifying frontend error handling.

For full request/response schemas and example payloads, see [`docs/api-contract.md`](../docs/api-contract.md).

---

## AWS Architecture

### Service Mapping

| AWS Service | Role | Configuration |
|---|---|---|
| **EC2** (t2.micro) | Application server running Flask + gunicorn | Auto-Scaling Group (min 1, max 4) |
| **ALB** | HTTPS termination, health checks, traffic distribution | Listens on port 443, routes to EC2 target group |
| **S3** | File storage for uploaded study materials | Keys: `uploads/{material_id}/{filename}` |
| **RDS** (MySQL, db.t3.micro) | Persistent storage for materials and generated results | Single-AZ, `cloudstudy` database |
| **Textract** | OCR for image files (PNG, JPG) | On-demand `detect_document_text` API calls |
| **Cognito** | User authentication, JWT issuance, TOTP MFA | User pool with hosted UI and OAuth2 flow |
| **VPC** | Network isolation | Public subnets (ALB), private subnets (EC2, RDS) |
| **CloudWatch** | Monitoring and alarms | CPU utilization, unhealthy host count |

### Data Flow

```
                          Upload Flow
                          ----------
User --> ALB (HTTPS) --> EC2/Flask --> S3 (store file)
                              |
                              +--> RDS (create material record)
                              |
                              +--> Background Thread:
                                     S3 (download) --> Textract/pdfplumber --> RDS (store text)

                          Generation Flow
                          ---------------
User --> ALB (HTTPS) --> EC2/Flask --> RDS (fetch extracted text)
                              |
                              +--> Gemini API (generate content)
                              |
                              +--> RDS (store results)
                              |
                              +--> JSON response to client
```

### Scalability

- **Stateless backend:** No local file storage or in-memory session state. All data lives in S3 and RDS. Any EC2 instance can serve any request.
- **Horizontal scaling:** The Auto-Scaling Group adds instances based on CPU utilization. The ALB distributes traffic across healthy instances.
- **Fault tolerance:** ALB health checks (`GET /api/health`) automatically remove unhealthy instances from the target group. New instances bootstrap from the launch template.

**Current constraints within the Learner Lab:**

- Background OCR threads are daemon threads tied to the worker process that spawned them. If the ASG terminates an instance during OCR, that job is lost and the material remains in `extracting` status. See [Design Tradeoffs](#design-tradeoffs-and-known-limitations) for the rationale behind this approach.
- Each database call opens a new connection. With the ASG scaled to 4 instances running 4 gunicorn workers each, peak connection demand could approach the db.t3.micro limit of roughly 66 connections.
- Gemini's free tier rate limits (10 RPM, 250 RPD) act as a throughput ceiling for AI generation, independent of how many EC2 instances are running.

### Reliability

- **Instance recovery:** The ASG automatically replaces terminated or unhealthy instances using the launch template. No manual intervention is needed to restore capacity.
- **Health monitoring:** ALB health checks poll `GET /api/health` and remove unresponsive instances from the target group within seconds.
- **Error persistence:** Failed AI generation attempts are saved to the database with an error message before the error is returned to the client. This preserves an audit trail for debugging (`pipeline.py`).
- **Accepted constraints:** Within the scope of the Learner Lab, the system does not implement OCR retry logic, a stuck-material recovery sweeper, or generation timeouts. These are acknowledged tradeoffs documented in [Design Tradeoffs](#design-tradeoffs-and-known-limitations).

### Frontend Deployment Strategy

The frontend is **not built on EC2**. It is built locally, uploaded to S3, and synced to EC2 instances during bootstrap. This reduces instance startup time from roughly 15 minutes (npm build on t2.micro) to roughly 90 seconds.

---

## Database Schema and Data Modeling

### Entity Relationship

```
materials (1) ----< (N) results
    |                      |
    +-- id (PK, UUID)      +-- id (PK, UUID)
    +-- filename           +-- material_id (FK)
    +-- s3_key             +-- result_type (ENUM)
    +-- file_type          +-- status (ENUM)
    +-- user_id            +-- content (JSON)
    +-- status (ENUM)      +-- format_hint
    +-- extracted_text     +-- error_message
    +-- error_message      +-- created_at
    +-- created_at         +-- updated_at
    +-- updated_at
```

### `materials` Table

| Column | Type | Purpose |
|---|---|---|
| `id` | `VARCHAR(36) PK` | UUID v4, generated server-side. Avoids exposing sequential IDs in URLs. |
| `filename` | `VARCHAR(255)` | Original upload filename (for display) |
| `s3_key` | `VARCHAR(512)` | Full S3 object key (`uploads/{id}/{filename}`) |
| `file_type` | `VARCHAR(10)` | File extension (pdf, png, docx, etc.) |
| `user_id` | `VARCHAR(255)` | Cognito `sub` claim (stable identifier, unlike email which can change) |
| `status` | `ENUM('extracting','ready','error')` | Pipeline state, enforced at the database level |
| `extracted_text` | `LONGTEXT` | Full text content after OCR/extraction (supports large documents) |
| `error_message` | `TEXT` | Failure reason, populated only when `status='error'` |
| `created_at` / `updated_at` | `DATETIME` | Audit timestamps |

### `results` Table

| Column | Type | Purpose |
|---|---|---|
| `id` | `VARCHAR(36) PK` | UUID v4 |
| `material_id` | `VARCHAR(36) FK` | References `materials(id)` |
| `result_type` | `ENUM('summary','quiz','flashcards')` | Generation type |
| `status` | `ENUM('done','error')` | Generation outcome |
| `content` | `JSON` | Generated content (structure varies by result_type) |
| `format_hint` | `TEXT` | Custom generation instructions from the user |
| `error_message` | `TEXT` | Failure details |

### Design Rationale

- **UUID primary keys:** Prevent enumeration attacks and avoid leaking information about record count or creation order.
- **ENUM columns:** Enforce valid state transitions at the database level, catching invalid values before they reach application logic.
- **JSON content column:** Each result type (summary, quiz, flashcards) has a different structure. A JSON column provides schema flexibility without additional tables.
- **Upsert pattern:** `save_result()` checks for an existing result with the same `(material_id, result_type)` pair. If found, it updates; otherwise, it inserts. This makes regeneration idempotent.

---

## Security

### Authentication: Cognito JWT Verification

All authenticated endpoints require a valid Cognito access token in the `Authorization: Bearer <token>` header. The `auth_service.py` module verifies tokens using the following process:

1. **Extract `kid`** from the JWT header (without verifying the token)
2. **Fetch the matching RSA public key** from Cognito's JWKS endpoint
3. **Verify the token** using RS256 algorithm, checking:
   - Cryptographic signature
   - Expiration (`exp` claim)
   - Issuer (must match the configured Cognito User Pool)
   - Client ID (Cognito access tokens use `client_id` instead of `aud`)
   - Token use (must be `access`, not `id`)

**JWKS caching:** Public keys are cached in a module-level dictionary with thread-safe access (`threading.Lock`). On cache miss, the service fetches from Cognito's JWKS endpoint. If the key is still not found (possible during key rotation), it retries the fetch once more before rejecting the token.

### Authorization: Defense-in-Depth

Authentication is enforced at **two independent layers**:

1. **Global `before_request` hook** (`register_auth_middleware`): Runs before every request. Skips only CORS preflight (`OPTIONS`) and explicitly public paths (`/api/health`). Sets `g.user_id` and `g.user_email` on success.
2. **Per-route `@require_auth` decorator**: Acts as a safety net. If the `before_request` hook was somehow bypassed (misconfiguration, future refactoring), this decorator independently verifies the token.

This dual-layer approach ensures that adding a new route without the decorator still requires authentication (via the global hook), while the decorator provides an explicit, visible contract on each protected endpoint.

### User Data Isolation

Every database query that returns user-facing data filters by `user_id` (the Cognito `sub` claim from the JWT):

```python
# db_service.py - get_material()
cur.execute("SELECT * FROM materials WHERE id=%s AND user_id=%s", (material_id, user_id))
```

This prevents users from accessing other users' materials or results, even if they guess or enumerate material IDs. Internal operations (such as the background OCR thread) that need to access materials without a user context are explicitly documented with a `WARNING` comment in the codebase.

### Input Validation

| Check | Location | Details |
|---|---|---|
| File extension whitelist | `routes/upload.py` | Only `pdf`, `docx`, `txt`, `md`, `png`, `jpg`, `jpeg` |
| Upload size limit | `config.py` | 10 MB max (`MAX_CONTENT_LENGTH`) |
| Result type validation | `routes/generate.py` | Must be one of `summary`, `quiz`, `flashcards` |
| File presence check | `routes/upload.py` | Rejects requests with no file or empty filename |

### Infrastructure Security

- **Secrets management:** All credentials (RDS password, Gemini API key, Cognito config) are loaded from environment variables via `python-dotenv`. No secrets are hardcoded.
- **CORS:** Configured with `CORS(app)`, which allows all origins. Within the Learner Lab environment where the frontend origin changes with each ALB redeployment, this avoids hardcoding a specific domain. In a fixed-domain setup, the allowed origin should be restricted.
- **HTTPS:** ALB terminates TLS (self-signed certificate for the Learner Lab environment).
- **Network isolation:** EC2 instances and RDS run in private subnets; only the ALB is in public subnets.
- **Parameterized queries:** All SQL uses `%s` placeholders via PyMySQL, preventing SQL injection.

---

## Development Workflow

### Prerequisites

- Python 3.11+
- MySQL (local instance or RDS endpoint)
- AWS credentials (from Learner Lab)
- Google Gemini API key

### Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt     # pytest and dev tools
cp .env.example .env                    # Fill in your values
```

### Environment Variables

All configuration is loaded from environment variables via `python-dotenv`. The table below lists every variable read by `config.py`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `FLASK_SECRET_KEY` | In production | `dev-secret-key` | Flask session signing key |
| `FLASK_ENV` | No | `development` | `development` or `production` |
| `FLASK_PORT` | No | `5000` | Server listen port |
| `AWS_REGION` | No | `us-east-1` | AWS region for S3 and Textract |
| `S3_BUCKET_NAME` | Yes | `cloudstudy-uploads-team10` | S3 bucket for file uploads |
| `RDS_HOST` | Yes | (empty) | MySQL endpoint (RDS or local) |
| `RDS_PORT` | No | `3306` | MySQL port |
| `RDS_DATABASE` | No | `cloudstudy` | Database name |
| `RDS_USERNAME` | No | `admin` | Database user |
| `RDS_PASSWORD` | Yes | (empty) | Database password |
| `GEMINI_API_KEY` | No | (empty) | Server-side Gemini key; optional if users supply their own via the `X-Gemini-Api-Key` header |
| `COGNITO_USER_POOL_ID` | Yes | (empty) | Cognito User Pool ID |
| `COGNITO_CLIENT_ID` | Yes | (empty) | Cognito App Client ID |
| `COGNITO_REGION` | No | `us-east-1` | Cognito region (used to construct the JWKS URL) |

### Running Locally

```bash
source venv/bin/activate
python run.py                           # Starts on http://localhost:5000
curl http://localhost:5000/api/health   # Verify: {"status": "ok"}
```

### Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

The test suite contains **74 tests across 9 files**, covering:

| Test File | Coverage Area |
|---|---|
| `test_health.py` | Health endpoint |
| `test_upload.py` | File upload validation and pipeline integration |
| `test_generate.py` | Generation endpoint and error handling |
| `test_results.py` | Results retrieval |
| `test_services.py` | Unit tests for all 5 service modules |
| `test_pipeline.py` | Pipeline orchestrator logic |
| `test_auth.py` | JWT verification and middleware |
| `test_user_scoping.py` | User data isolation (cross-tenant access prevention) |
| `conftest.py` | Shared fixtures (Flask test client) |

**Test architecture:** The `TESTING=True` config flag skips Cognito JWT verification (sets a default test user) and skips database table creation, allowing tests to run without AWS credentials or a live database.

### Production Deployment

In production, the backend runs under **gunicorn** behind the ALB:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

EC2 instances are launched via the Auto-Scaling Group with a launch template that installs dependencies and starts gunicorn automatically.

### Logging

The backend uses Python's built-in `logging` module in service modules (e.g., `ai_service.py`) and Flask's `current_app.logger` in route handlers. Logs are plain text written to stdout/stderr, which gunicorn captures automatically.

In the deployed environment, logs can be accessed by SSH-ing into the EC2 instance and reading gunicorn's output. If the CloudWatch agent is configured on the instance, logs are also forwarded to CloudWatch Logs for centralized access. No structured logging format (e.g., JSON lines) is currently implemented.

---

## Future Improvements

These improvements are grounded in limitations observed in the current architecture:

| Improvement | Current Limitation | Benefit |
|---|---|---|
| **Celery + SQS** for async processing | `threading.Thread` has no retry logic, no dead-letter queue, and no visibility into failed jobs | Production-grade task queue with retries, monitoring, and horizontal scaling |
| **Connection pooling** (e.g., SQLAlchemy pool or PyMySQL pool) | Each request opens and closes a new database connection | Reduces connection overhead, especially under concurrent load |
| **Rate limiting** on `/api/generate` | No enforcement of Gemini's free tier limits (10 RPM, 250 RPD) | Prevents 429 errors from Gemini and provides graceful degradation |
| **OpenAPI / Swagger** documentation | API contract is a manually maintained Markdown file | Auto-generated, interactive docs that stay in sync with code |
| **Result caching** | Regenerating the same content type makes a new Gemini API call every time | Avoids redundant API calls for unchanged source material |
| **Alembic migrations** | Schema changes require manual `CREATE TABLE` / `ALTER TABLE` statements | Versioned, reversible schema migrations tracked in source control |
