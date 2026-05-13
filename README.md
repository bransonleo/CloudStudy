# CloudStudy: AI-Powered Study Assistant

> Singapore Institute of Technology  
> CSD3156 Mobile and Cloud Computing  
> AY 2025/2026, Trimester 2  
> Cloud Computing Project Team 10

CloudStudy is a cloud-based web application that helps students study more effectively. Students upload their study materials (PDFs, Word documents, Markdown, plain text, or images) and the system automatically extracts text and uses AI to generate summaries, quiz questions, and flashcards.

Preparing structured study content manually is time-consuming. CloudStudy automates this process, letting students focus on learning rather than reformatting notes. The application is built on AWS with an N-tier architecture designed for scalability, reliability, elasticity, and security.

## Features

- Upload study materials (PDF, Word documents, Markdown, plain text, images)
- Automatic text extraction (cloud OCR for images, local parsing for documents)
- AI-generated summaries of study content
- AI-generated multiple-choice quiz questions
- AI-generated flashcards for revision
- Cognito-based user authentication with optional user-enabled TOTP MFA
- Per-user data isolation (users only see their own materials)
- Upload history and result browsing

## System Architecture

### Architecture Diagram

```mermaid
graph TB
    User["End User<br/>(Browser, HTTP)"]

    subgraph AWS["AWS Region: us-east-1"]
        Cognito["Amazon Cognito User Pool<br/>RS256 JWT, optional TOTP<br/>JWKS endpoint"]
        Textract["Amazon Textract<br/>(regional service)"]

        subgraph VPC["VPC 10.0.0.0/16"]
            subgraph PubA["Public Subnet AZ-a (10.0.1.0/24)"]
                ALB1["ALB node<br/>(HTTP :80)"]
                NAT["NAT Gateway"]
            end
            subgraph PubB["Public Subnet AZ-b (10.0.2.0/24)"]
                ALB2["ALB node"]
            end
            subgraph PrivA["Private Subnet AZ-a (10.0.3.0/24)"]
                EC2A["EC2 t2.micro<br/>Nginx + Flask + gunicorn<br/>(ASG member)"]
                RDSA["RDS MySQL<br/>(primary)"]
            end
            subgraph PrivB["Private Subnet AZ-b (10.0.4.0/24)"]
                EC2B["EC2 t2.micro<br/>Nginx + Flask + gunicorn<br/>(ASG member)"]
            end
            IGW["Internet Gateway"]
        end

        S3["Amazon S3<br/>(pre-provisioned bucket)"]
        CW["CloudWatch<br/>Logs + CPU alarms"]
    end

    Gemini["Google Gemini API<br/>gemini-2.5-flash"]

    User -->|HTTP 80| IGW
    IGW --> ALB1
    IGW --> ALB2
    ALB1 -->|HTTP 80<br/>nginx proxy| EC2A
    ALB2 --> EC2B
    EC2A -->|IAM role| S3
    EC2A -->|MySQL 3306<br/>(private subnet)| RDSA
    EC2B --> RDSA
    EC2A -->|NAT| Gemini
    EC2A -->|IAM role| Textract
    EC2A -.->|JWKS fetch + JWT verify| Cognito
    EC2A -.->|logs, metrics| CW
    CW -.->|CPU alarm| EC2A
```

> Subnet and connection details shown for one AZ apply symmetrically to the other. EC2 access to S3, RDS, Gemini, and Textract applies to all ASG members.

<details>
<summary>ASCII fallback (for viewers without Mermaid support)</summary>

```
Users (Browser)
      |
      v
+-----------+
| Frontend  |  React (Vite) + TypeScript
+-----+-----+
      | HTTP (80)
      v
+-------------------+
| Application Load  |  HTTP listener, routes traffic
| Balancer (ALB)    |  to backend via nginx
+-----+-------------+
      |
+-----v-----------------+
| Auto-Scaling Group    |
| +--------+ +--------+ |
| | EC2    | | EC2    | |  Nginx + Python Flask (gunicorn)
| | Backend| | Backend| |  t2.micro instances (2 AZs)
| +---+----+ +---+----+ |
+-----+----------+------+
      |          |
  +---v---+ +----v---+ +----------+ +---------+
  |  S3   | |  RDS   | |  Gemini  | | Textract|
  |(files)| |(MySQL) | | API (AI) | |  (OCR)  |
  +-------+ +--------+ +----------+ +---------+
```

</details>

### Service Mapping

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | React (Vite) + TypeScript | Single-page application served via Nginx on EC2 |
| Load Balancer | AWS ALB | HTTP listener on port 80, health checks, traffic distribution across AZs |
| Reverse Proxy | Nginx | HTTP 80 listener on EC2 instances, proxies /api/ to Flask 127.0.0.1:5000, serves static frontend |
| Backend | Python Flask + gunicorn | REST API endpoints, request orchestration, business logic, background pipelines |
| File Storage | Amazon S3 (pre-provisioned) | Stores uploaded study materials under `uploads/<material_id>/<filename>` |
| Database | Amazon RDS MySQL (pre-provisioned) | Two tables: `materials` and `results` (see Data Model) |
| AI Generation | Google Gemini API (`gemini-2.5-flash`) | Generates `summary`, `quiz`, or `flashcards` JSON from extracted text |
| OCR | Amazon Textract (`detect_document_text`) | Extracts text from `png`/`jpg`/`jpeg` uploads |
| Authentication | Amazon Cognito User Pool | User sign-up/sign-in, RS256 access tokens, optional user-enabled TOTP MFA |
| Networking | VPC with public/private subnets across 2 AZs | Public subnets host the ALB and NAT Gateway; private subnets host the EC2 ASG and the RDS endpoint. Outbound traffic from private subnets egresses via the NAT Gateway. |
| Scaling | Auto-Scaling Group + CloudWatch alarms | Horizontal scaling between 1 and 4 `t2.micro` instances on CPU thresholds with a 120 s cooldown |
| Observability | CloudWatch metrics + 2 alarms | AWS/EC2 `CPUUtilization` drives the scale-out and scale-in alarms defined in [infra/app.yaml](infra/app.yaml) |

## How It Works

### Authentication Flow

1. The user visits the frontend; `ProtectedRoute` redirects unauthenticated users to `/login`
2. `LoginPage.tsx` redirects the browser to the Cognito Hosted UI (`getCognitoLoginUrl()`) for sign-up or sign-in
3. After successful authentication, Cognito redirects back to `/callback?code=<auth_code>`
4. `CallbackPage.tsx` calls `exchangeCodeForTokens(code)`, which POSTs to the Cognito `/oauth2/token` endpoint using the Authorization Code grant and receives an RS256 `id_token`, `access_token`, and `refresh_token`
5. The tokens are persisted to `localStorage` (and mirrored into `AuthContext` React state); `api/client.ts` reads the access token from `localStorage` and attaches it as `Authorization: Bearer <access_token>` on every subsequent API call
6. Signed-in users may optionally enrol a TOTP authenticator via `TwoFactorPage.tsx` to require MFA on subsequent sign-ins

### Upload Flow

1. The user selects a file in the React frontend
2. The frontend sends the file to `POST /api/upload` with a Cognito access token
3. The ALB routes the request to an available EC2 instance
4. The backend validates the file type (allowlist: `pdf`, `docx`, `md`, `txt`, `png`, `jpg`, `jpeg`) and size (max 10 MB), uploads it to S3, and creates a record in RDS with status `extracting`
5. The backend spawns a background thread for text extraction
6. The API returns HTTP 202 (Accepted) immediately, so the user is not blocked
7. The background thread downloads the file from S3, extracts text using the appropriate method (Textract for images, pdfplumber for PDFs, python-docx for Word documents, UTF-8 decode for text/Markdown), and updates the material status to `ready` with the extracted text, or to `error` with an error message if extraction fails
8. The frontend polls the results endpoint until the status changes from `extracting` (to either `ready` or `error`)

### Generation Flow

1. The user selects a generation type: summary, quiz, or flashcards
2. The frontend sends `POST /api/generate/<material_id>` with the chosen type
3. The backend retrieves the extracted text from RDS and sends it to the Gemini API with a structured prompt requesting JSON output
4. Gemini returns the generated content as JSON, which the backend parses and stores in RDS
5. The frontend retrieves and displays the results (summary view, interactive quiz, or flip-card flashcards)

## Data Model

**`materials`**

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) | UUID primary key |
| `user_id` | VARCHAR(255) | Cognito `sub` claim of the uploader |
| `filename` | VARCHAR(255) | Original upload filename |
| `s3_key` | VARCHAR(512) | Object key in the S3 bucket (`uploads/<id>/<filename>`) |
| `file_type` | VARCHAR(10) | Lowercased file extension: `pdf`, `docx`, `txt`, `md`, `png`, `jpg`, `jpeg` |
| `status` | ENUM | `extracting` \| `ready` \| `error` |
| `extracted_text` | LONGTEXT | Populated after OCR/parse; NULL if `error` |
| `error_message` | TEXT NULL | Populated on `error` status |
| `created_at` | DATETIME | UTC creation timestamp |
| `updated_at` | DATETIME | UTC last update timestamp |

**`results`**

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) | UUID primary key |
| `material_id` | VARCHAR(36) | FK → `materials.id` |
| `result_type` | ENUM | `summary` \| `quiz` \| `flashcards` |
| `status` | ENUM | `done` \| `error` |
| `content` | JSON | Gemini output (summaries, quizzes, flashcards); NULL on `error` |
| `format_hint` | TEXT NULL | User-provided formatting guidance for Gemini |
| `error_message` | TEXT NULL | Populated on `error` status |
| `created_at` | DATETIME | UTC creation timestamp |
| `updated_at` | DATETIME | UTC last update timestamp |

Authorization is enforced at the material level: the routes that read a material pass `g.user_id` (from the verified JWT) into `db_service.get_material(material_id, user_id)`, which issues `SELECT * FROM materials WHERE id=%s AND user_id=%s`. Generation and results fetches are reached through the same ownership check before any `results` row is returned, so the `results` table does not need a denormalised `user_id` column.

## API Reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | none | ALB health probe; returns `200 {"status":"ok"}` |
| POST | `/api/upload` | JWT | Accepts a single `file` multipart field; returns `202` with `material_id` and `status:"extracting"` |
| POST | `/api/generate/<material_id>` | JWT | Synchronous Gemini generation; returns `200` on success, `404` if the material is not owned by the caller, `409` if still extracting, `422` if extraction previously failed, `500` on Gemini/parse errors |
| GET | `/api/results/<material_id>` | JWT | Returns material status plus the current `summary`/`quiz`/`flashcards` result rows (each labelled `not_requested`, `done`, or `error`) |

JWT-protected routes return `401` on missing or invalid tokens and `404` on cross-user access (never `403`, to avoid leaking resource existence). The generate endpoint optionally accepts an `X-Gemini-Api-Key` header (bring-your-own-key override) and an optional `format_hint` body field forwarded into the Gemini prompt.

## Quality Attributes

### Functionality

End-to-end flows (upload, OCR/parse, AI generation, retrieval) are deployed on AWS and verified by a **74-test pytest suite** covering route handlers, service wrappers (S3, RDS, Textract, Gemini, Cognito), the OCR pipeline, JWT middleware, and per-user data isolation. A GitHub Actions CI workflow automatically runs:
- Backend: `pytest tests/ -v` (all 74 tests) on every push to `main`/`dev` and on pull requests
- Frontend: `npm run lint` (ESLint) and `npm run build` (Vite production build) on every push to `main`/`dev` and on pull requests

The workflow fails if any test fails or if linting/build steps fail, providing continuous feedback on code quality.

### Scalability

- **Stateless HTTP handling.** Every protected request re-verifies a Cognito JWT against cached JWKS keys; no session state is held in process memory or on local disk. All durable state lives in S3 (files) or RDS (rows), so any EC2 instance can serve any request and the ALB distributes traffic across healthy targets without sticky sessions.
- **Horizontal scaling mechanism.** An Auto-Scaling Group manages `t2.micro` instances across two AZs (`MinSize=1`, `DesiredCapacity=2`, `MaxSize=4`), driven by the two CloudWatch CPU alarms described under Elasticity.
- **Stateful caveat: background extraction.** OCR/parse runs as in-process daemon `threading.Thread` jobs on the instance that accepted the upload, so an in-flight extraction is bound to its host even though HTTP handling is stateless. The `materials.status` column (`extracting`/`ready`/`error`) lets the client recover state via polling.
- **Database bottleneck.** Each request opens a fresh PyMySQL connection (no pooling), so the single RDS MySQL instance is the first resource expected to saturate under load. Concrete ceiling: gunicorn runs with `--workers 2` per instance (see [infra/app.yaml](infra/app.yaml)), so at `MaxSize=4` the ASG holds at most 8 synchronous request workers. Peak concurrent connections are bounded by those 8 workers plus any in-flight extraction daemon threads, which sits well below the default connection limit of a `db.t3.micro` RDS MySQL instance. Documented scaling path: vertical first, then read replicas for the read-dominant results endpoint. Neither is applied in Learner Lab.
- **Gemini as an external boundary.** Gemini free-tier quotas cap generation throughput independently of EC2 capacity. On any Gemini failure (rate limit, parse error, network), the pipeline writes a `results` row with `status='error'` and returns `500` so the client can retry explicitly.

### Reliability

**Health checks and self-healing.** The ALB target group probes `GET /api/health` every 30 s with `HealthyThresholdCount=2` and `UnhealthyThresholdCount=3`, so an instance is removed after 90 s of failed probes and re-registered after 60 s of successful ones. The ASG uses `HealthCheckType: ELB` and a 300 s grace period, so unhealthy instances are terminated and replaced from the launch template automatically. With `DesiredCapacity: 2`, a single-instance failure is absorbed immediately by the peer.

**Multi-AZ redundancy.** The ASG spans both private subnets (`CloudStudy-PrivateSubnet1Id`, `CloudStudy-PrivateSubnet2Id`) and the ALB spans both public subnets, so a full AZ outage degrades the system to reduced capacity rather than a full outage.

**Durability of application state.** Every upload writes a `materials` row before the API returns `202`, and every generation attempt writes a `results` row with terminal status (`done` or `error`) before the API responds, so no client-visible operation succeeds without a persisted audit trail. The underlying S3 bucket and RDS instance are pre-provisioned Learner Lab resources passed into the stack as parameters; their encryption, versioning, and backup settings live outside this template.

**Failure accountability.** Every terminal state is persisted before the HTTP response returns: uploads insert a `materials` row with `status='extracting'` prior to `202`, then the background thread commits `ready` or `error` to the same row; generation writes a `results` row with `done`/`error` before responding. Consequences:
1. A client disconnect mid-response does not lose progress; a refresh recovers the final state from RDS.
2. Every failure leaves an auditable row in the database with an error message.
3. There are no silent failures: every generation attempt produces either a `done` row or an `error` row.

**Known reliability boundary.** In-process background extraction threads are not resilient to gunicorn worker restarts. If a worker crashes during extraction, the affected material row stays in `extracting` state indefinitely. Blast radius: only in-flight uploads are affected; all persisted results are durable. The production mitigation is Celery + SQS with visibility-timeout retries and a DLQ.

**Manual recovery for stuck rows.** Because `materials.updated_at` is refreshed on every state transition, an operator can identify and mark stuck rows with a single SQL statement:

```sql
UPDATE materials
SET status = 'error',
    error_message = 'extraction abandoned after worker restart',
    updated_at = NOW()
WHERE status = 'extracting'
  AND updated_at < NOW() - INTERVAL 10 MINUTE;
```

The frontend then surfaces the `error` state on the next poll and the user can re-upload. This is a manual cleanup, not an automated sweeper; a production deployment would run the equivalent as a scheduled task.

### Elasticity

Elasticity is distinct from scalability here: scalability is the *capability*, elasticity is the *automatic, demand-driven adjustment*.

- **Metric and thresholds.** Simple alarms on average ASG CPU utilization: scale-out when CPU > **60%** sustained for 2 minutes (2 periods of 60s), scale-in when CPU < **30%** for 5 minutes (5 periods of 60s). CPU is chosen over request count because the generation path is Gemini-latency-bound and bursty per request.
- **Bounds.** `min=1, desired=2, max=4`. ASG launches with 2 instances (one per AZ) to start; the lower bound of 1 is a Learner Lab cost constraint during scale-in; production would set `min=2` for permanent AZ redundancy.
- **Cooldowns.** `Cooldown: 120` on both scale-out and scale-in policies (see [infra/app.yaml](infra/app.yaml)) prevents oscillation while a newly-launched instance is still inside its ASG health-check grace period.
- **Scale-in protection.** Instance-level scale-in protection is disabled because there are no long-lived in-memory jobs longer than ~60 s (Gemini API calls), so losing an instance during scale-in at worst fails a single in-flight request, which the client retries.
- **Feedback loop.** The same AWS/EC2 `CPUUtilization` metric that feeds the two alarms is visible in the CloudWatch console, giving operators and the autoscaler a single source of truth.

### Security

Defence-in-depth is implemented across four layers (network, identity, application, data); each layer is described below with the concrete mechanism that enforces it.

**Threat model (in scope).**
1. **Unauthenticated API access.** Rejected at the Flask `before_request` middleware before any route handler or database query runs.
2. **Cross-user data access.** Blocked by a `WHERE id=%s AND user_id=%s` filter on the `materials` ownership query; cross-user lookups return `404`.
3. **SQL injection.** All SQL statements in [backend/app/services/db_service.py](backend/app/services/db_service.py) use PyMySQL `%s` placeholders; no string concatenation or f-strings appear in query text.
4. **Network exposure of internal services.** EC2 and the RDS endpoint sit in private subnets and are reachable only through security-group references (not CIDRs).
5. **Accidental secret commits.** Only `.env.example` is checked in; runtime secrets are injected from `NoEcho` CloudFormation parameters into `/opt/cloudstudy/backend/.env` via `UserData`.

**Out of scope.** AWS account/IAM compromise, supply-chain attacks on third-party dependencies, zero-days in Flask/PyMySQL/nginx, compromise of Cognito itself, and state-sponsored APT activity are not defended against.

**Network isolation.** Defined in [infra/network.yaml](infra/network.yaml):
- EC2 and the RDS endpoint live in private subnets (`10.0.3.0/24`, `10.0.4.0/24`); only the ALB is internet-facing, in public subnets `10.0.1.0/24` and `10.0.2.0/24`.
- `ALBSecurityGroup` allows inbound HTTP `:80` from `0.0.0.0/0`.
- `EC2SecurityGroup` allows inbound HTTP `:80` only from `ALBSecurityGroup` (security-group reference, not a CIDR).
- `RDSSecurityGroup` allows inbound MySQL `:3306` only from `EC2SecurityGroup`.
- No inbound SSH or RDP rules from the internet exist on any security group.
- Outbound traffic from private subnets (for Gemini API calls) egresses through the NAT Gateway; backend instances have no public IPs.

**Identity and authentication.** Implemented in [backend/app/middleware/auth.py](backend/app/middleware/auth.py) and [backend/app/services/auth_service.py](backend/app/services/auth_service.py):
- Users authenticate via the Amazon Cognito User Pool, which issues RS256 access tokens. The frontend includes a TOTP enrolment page (`TwoFactorPage.tsx`) that lets a signed-in user opt into software-token MFA; MFA is therefore available but not forced for every account.
- Every protected request must carry `Authorization: Bearer <token>`.
- `verify_token()` fetches the JWKS from `https://cognito-idp.<region>.amazonaws.com/<pool>/.well-known/jwks.json` and caches public keys by `kid` in memory. A `kid` miss triggers a re-fetch, which supports Cognito key rotation without a restart.
- Signature verification runs through `jwt.decode(..., algorithms=["RS256"], issuer=expected_issuer)`. PyJWT enforces `exp` during `decode`.
- On top of that, the middleware explicitly validates `claims["client_id"] == COGNITO_CLIENT_ID` and `claims["token_use"] == "access"` to reject tokens issued for other clients or token types.
- Failed verification raises `InvalidTokenError`, which the middleware converts to `401` before any route handler or database query runs.
- Authentication is attached at two layers: the global `before_request` hook and a `@require_auth` decorator on each protected route. The decorator is a pass-through when `before_request` has already populated `g.user_id`, and otherwise re-verifies the token itself.

**Authorisation and data isolation.** Every currently-exposed route that touches a `materials` row passes `g.user_id` (derived from the JWT's verified `sub` claim) into `db_service.get_material(material_id, user_id)`, which runs `SELECT * FROM materials WHERE id=%s AND user_id=%s`. A cross-user lookup therefore matches zero rows and the route returns `404` rather than `403`. `backend/tests/test_user_scoping.py` exercises this path: a second authenticated user cannot read, generate from, or retrieve results for another user's material.

**Application input handling.**
- **Upload size cap.** `MAX_CONTENT_LENGTH = 10 * 1024 * 1024` in [backend/app/config.py](backend/app/config.py); Flask rejects oversize requests at the WSGI parsing stage with `413`.
- **Extension allowlist.** `ALLOWED_EXTENSIONS = {pdf, png, jpg, jpeg, txt, md, docx}`. The upload route reads the lowercased extension via `filename.rsplit(".", 1)[1].lower()` and returns `400` on any non-matching extension. The application itself never executes or serves uploaded files; S3 objects are retrieved only by the backend pipeline.
- **Parameterised SQL.** Every `cur.execute(...)` call in [backend/app/services/db_service.py](backend/app/services/db_service.py) uses `%s` placeholders with a separate parameter tuple. A repository-wide search confirms no f-strings or string concatenation are used to build SQL.
- **Prompt scaffolding.** `ai_service._build_prompt(text, result_type, format_hint)` wraps the extracted text inside a fixed instructional template before calling `gemini-2.5-flash`. If the Gemini response cannot be parsed with `json.loads()`, the pipeline persists a `results` row with `status='error'` and the error message, and the route returns `500`.

**Data at rest and in transit.**
- S3: the bucket is pre-provisioned outside the CloudFormation stack. It is configured with SSE-S3 default encryption and public-access-block at the account/bucket level (Learner Lab default); the application never generates public URLs and never serves user files directly from Flask.
- RDS: the database instance is also pre-provisioned and reached only through a private-subnet security group. In-transit TLS (`ssl_ca`) is not configured between EC2 and RDS; this is acceptable only because both sides live in the same VPC behind a security-group allowlist, and is called out as a production hardening item under Limitations.
- ALB: HTTP listener on port 80 (`ALBListener` in [infra/app.yaml](infra/app.yaml)). No TLS is terminated at the ALB because Learner Lab does not permit ACM certificates or custom domains. This is the single biggest residual risk and is documented under Limitations.

**Secrets.** The RDS password and Gemini API key are passed as `NoEcho` CloudFormation parameters and rendered into `/opt/cloudstudy/backend/.env` by user-data on each instance. The Flask `SECRET_KEY` is generated per instance with `secrets.token_hex(32)` at bootstrap. The repository contains only `.env.example`; no secret material is committed, and GitHub Actions does not receive production credentials.

**IAM.** EC2 instances attach the Learner Lab `LabInstanceProfile` (`IamInstanceProfile: LabInstanceProfile` in [infra/app.yaml](infra/app.yaml)). This role is provided by the lab environment and is broader than a least-privilege production role would be; we cannot modify it. The application mitigates the blast radius by only ever calling a small set of APIs (`s3:GetObject`/`s3:PutObject` on the project bucket prefix, `textract:DetectDocumentText`, and `logs:PutLogEvents`) and by never persisting or forwarding AWS credentials to the client. A production deployment would replace `LabInstanceProfile` with a bespoke role scoped to exactly those actions on exactly those resources.

## Observability

- **Logs.** Gunicorn and Flask write to the systemd journal on each instance; the journal is collected by the Learner Lab CloudWatch agent where available. Log retention follows the Learner Lab default.
- **Metrics.** Out-of-the-box AWS/EC2 `CPUUtilization` (per ASG) and AWS/ApplicationELB target metrics (`RequestCount`, `TargetResponseTime`, `HTTPCode_Target_5XX_Count`, `UnHealthyHostCount`). No custom application metrics are published.
- **Alarms.** Two CloudWatch alarms are defined in [infra/app.yaml](infra/app.yaml): `HighCPUAlarm` (scale-out at CPU > 60% for 2×60 s) and `LowCPUAlarm` (scale-in at CPU < 30% for 5×60 s). No additional alarms on 5xx or unhealthy-host count are provisioned; this is a known observability gap listed under Future Improvements.
- **Tracing.** Not implemented. X-Ray would require additional IAM and latency overhead not justified at class-project scale.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Background processing | Python `threading.Thread` instead of Celery + SQS | Avoids the operational cost of a message broker at class-project scale. Trade-off: an in-flight extraction is lost if the gunicorn worker restarts, leaving its `materials` row stuck in `extracting`. Persisted results are unaffected. |
| Database access | Raw SQL via PyMySQL instead of an ORM | Only two tables exist, so an ORM would add abstraction without benefit. All queries use parameterised placeholders. |
| AI provider | Google Gemini free tier instead of AWS Bedrock | Zero cost at student scale, with structured JSON output. Users may override the server key per request via the `X-Gemini-Api-Key` header. |
| OCR strategy | Textract for images, pdfplumber for PDFs, python-docx for Word, UTF-8 decode for text/Markdown | Cloud OCR is reserved for the only format that needs it, reducing Textract API calls. |
| Frontend deployment | Pre-built locally, pushed to S3, synced via `aws s3 sync` in `UserData` | The [infra/app.yaml](infra/app.yaml) `UserData` comment notes this takes ~5 s per instance versus roughly 15 minutes for an on-instance `npm run build` on `t2.micro`, keeping ASG bootstrap within the 5-minute health-check grace period. |

## Project Structure

```
CloudStudy/
├── .github/workflows/  # CI pipeline (pytest + ESLint + build on push)
├── backend/            # Flask REST API, services layer, pipeline orchestrator
│   ├── app/
│   │   ├── routes/     # API endpoint blueprints (health, upload, generate, results)
│   │   ├── services/   # AWS and AI service wrappers (S3, RDS, Textract, Gemini, Cognito)
│   │   └── middleware/ # JWT authentication middleware
│   └── tests/          # Pytest suite (74 tests)
├── frontend/           # React + TypeScript SPA (Vite)
│   └── src/
│       ├── pages/      # Login, Callback, Dashboard, Upload, Result, History, TwoFactor, ApiKey
│       ├── components/ # Navbar, FileDropZone, FlashCard, QuizQuestion, ProtectedRoute
│       ├── context/    # Auth context (Cognito session state)
│       └── api/        # Fetch client, Cognito helpers
├── infra/              # CloudFormation stacks, deploy/teardown scripts
└── docs/               # Project documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20.19+ and npm
- AWS CLI v2 (configured with Learner Lab credentials)
- Google Gemini API key ([get one here](https://aistudio.google.com/))

### Backend Setup

**Linux / macOS:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env    # Then fill in your keys
python run.py
```

**Windows:**

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
copy .env.example .env
REM Then fill in your keys
python run.py
```

The backend runs at `http://localhost:5000`. Verify with:

```bash
curl http://localhost:5000/api/health
```

### Running Tests

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
python -m pytest tests/ -v
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

### Infrastructure Deployment

See [infra/README.md](infra/README.md) for full deployment details. A single script handles the entire AWS deployment:

```bash
bash infra/deploy.sh <rds-password> <gemini-api-key>
```

Teardown:

```bash
bash infra/teardown.sh
```

## Failure Modes and Mitigations

| Failure | Detection | Mitigation | Residual Risk |
|---|---|---|---|
| EC2 crash | ALB health check (3 failed probes) | ASG replaces instance from launch template | In-flight extraction on that instance is lost (status stays `extracting`) |
| AZ outage | ALB + ASG across 2 AZs | Surviving AZ continues to serve | Reduced capacity until ASG re-balances |
| RDS unavailability | PyMySQL connection errors surface as `500` | Operator-initiated restore from the Learner Lab RDS snapshot policy | Single-AZ RDS; downtime until manual restore |
| Gemini rate limit / error | Exception caught in pipeline | Result row written with `status=error` + error message | User must re-trigger generation |
| Invalid / expired JWT | Middleware `401` | Frontend refresh flow via Cognito | - |
| Malformed upload | MIME allowlist + size cap (10 MB) | `400` with error message | - |
| SQL injection attempt | Parameterized queries (PyMySQL) | Structural prevention | - |

## Limitations

- **In-process background extraction.** OCR/parse runs on daemon threads inside gunicorn workers and is not resilient to worker restarts. See the Reliability section for blast radius, manual recovery SQL, and the Celery + SQS production fix.
- **No TLS at the ALB.** The ALB listener is HTTP-only on port 80. Learner Lab constraints prevent HTTPS (no custom domain, no ACM). Production setup would use ACM with a custom domain and an HTTPS listener.
- **No connection pooling.** Each request opens a fresh PyMySQL connection. Adequate for expected concurrency on `t2.micro`; SQLAlchemy `QueuePool` or RDS Proxy is the upgrade path.
- **No server-side rate limiting.** Gemini free tier (10 RPM / 250 RPD) is the implicit limit. Explicit per-user token-bucket limiting is listed under Future Improvements.
- **CORS allows all origins (`*`).** The ALB DNS changes per Learner Lab redeploy, so a fixed allowlist is impractical. All state-changing endpoints still require a valid JWT, so CORS is not the security boundary.
- **RDS single-AZ.** Learner Lab cost constraint. Multi-AZ RDS is a one-parameter change in the CloudFormation template.

## Future Improvements

- Replace threading with Celery + SQS for background processing with retries and dead-letter queues
- Add database connection pooling to reduce connection overhead
- Implement server-side rate limiting on generation endpoints
- Use a custom domain with a CA-signed TLS certificate
- Cache generated results to avoid redundant Gemini API calls for unchanged source material

## Team

| Name | Role | Student ID |
|------|------|------------|
| Leo Yew Siang, Branson | Backend & AI Engineer | 2301321 |
| Chiu Jun Jie | Technical PM | 2301524 |
| Chua Sheng Kai Jovan | Frontend Developer | 2301244 |
| Cheong Jia Zen | Data & Security Engineer | 2301549 |

## Acknowledgements

Developed for CSD3156 Mobile and Cloud Computing, Singapore Institute of Technology.
