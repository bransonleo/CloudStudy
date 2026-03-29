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

> **Note:** S3 integration is pending. The endpoint currently validates the
> file and returns a stub `material_id`. Actual storage will be added in the
> next task.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | The study material to upload |

**Allowed file types:** `pdf`, `png`, `jpg`, `jpeg`, `txt`
**Max file size:** 10 MB

**Response `200 OK`:**
```json
{
  "material_id": "26a61f63-8eed-4298-8f2f-63f3929dd627",
  "filename": "lecture-notes.pdf",
  "message": "File uploaded successfully"
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
| 413 | File too large (exceeds 10 MB) |
| 500 | Internal server error |

---

## Planned Endpoints (not yet implemented)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Generate summary / quiz / flashcards for a material |
| GET | `/api/results/<material_id>` | Retrieve generated results |
| POST | `/api/auth/login` | Cognito login (JWT exchange) |
| POST | `/api/auth/logout` | Invalidate session |
