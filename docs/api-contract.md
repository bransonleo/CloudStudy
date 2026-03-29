# CloudStudy API Contract

Base URL (local dev): `http://localhost:5000`  
All endpoints prefixed with `/api/`.  
All responses are `application/json`.

---

## Health Check

### `GET /api/health`

Returns server status. Used by the ALB health check and monitoring.

**Request:** No body required.

**Response `200 OK`:**
```json
{
  "status": "ok"
}
```

---

## File Upload

### `POST /api/upload`

Upload a study material file. Validates file type and returns a `material_id`
for use in subsequent generate calls.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | The study material to upload |

**Allowed file types:** `pdf`, `png`, `jpg`, `jpeg`, `txt`
**Max file size:** 10 MB

**Response `202 Accepted`:**
```json
{
  "material_id": "26a61f63-8eed-4298-8f2f-63f3929dd627",
  "status": "extracting"
}
```

**Response `400 Bad Request` (no file):**
```json
{
  "error": "No file provided",
  "status": 400
}
```

**Response `400 Bad Request` (disallowed type):**
```json
{
  "error": "File type not allowed. Allowed: jpeg, jpg, pdf, png, txt",
  "status": 400
}
```

---

## AI Generation

### `POST /api/generate/<material_id>`

Trigger AI generation for an uploaded material. The material must have finished
OCR extraction (status `ready`) before generation can be requested.

**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | One of: `summary`, `quiz`, `flashcards` |
| `format_hint` | string | No | Optional instruction for quiz format (e.g. "3 true/false questions") |

**Response `200 OK`:**
```json
{
  "result_id": "a1b2c3d4-...",
  "material_id": "26a61f63-...",
  "type": "summary",
  "content": {
    "title": "Lecture Notes",
    "key_points": ["Point A", "Point B"],
    "summary": "A brief overview..."
  },
  "format_hint": null
}
```

**Response `400 Bad Request` (missing or invalid type):**
```json
{ "error": "type must be one of: summary, quiz, flashcards", "status": 400 }
```

**Response `404 Not Found` (material does not exist):**
```json
{ "error": "Material not found", "status": 404 }
```

**Response `409 Conflict` (OCR still running):**
```json
{ "error": "Material still processing", "status": 409 }
```

**Response `422 Unprocessable Entity` (OCR failed):**
```json
{ "error": "Text extraction failed: <reason>", "status": 422 }
```

**Response `500 Internal Server Error` (AI parsing failed):**
```json
{ "error": "AI response could not be parsed", "status": 500 }
```

### `GET /api/results/<material_id>`

Retrieve the material's OCR status and all generated AI content.

**Request:** No body required.

**Response `200 OK`:**
```json
{
  "material_id": "26a61f63-...",
  "filename": "lecture-notes.pdf",
  "status": "ready",
  "error_message": null,
  "results": {
    "summary": {
      "status": "done",
      "content": { "title": "...", "key_points": [], "summary": "..." }
    },
    "quiz": { "status": "not_requested" },
    "flashcards": { "status": "not_requested" }
  }
}
```

Material `status` values: `extracting` | `ready` | `error`
Result `status` values: `done` | `error` | `not_requested`

**Response `404 Not Found`:**
```json
{ "error": "Material not found", "status": 404 }
```

---

## Error Responses

All error responses follow this shape:

```json
{
  "error": "<human-readable message>",
  "status": <HTTP status code>
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (missing file, invalid type) |
| 404 | Route not found |
| 409 | Conflict (material still processing) |
| 413 | File too large (exceeds 10 MB) |
| 422 | Unprocessable entity (OCR extraction failed) |
| 500 | Internal server error |

---

## Planned Endpoints (not yet implemented)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Cognito login (JWT exchange) |
| POST | `/api/auth/logout` | Invalidate session |
