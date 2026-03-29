# Frontend Implementation — CloudStudy

**Date:** 2026-03-29
**Author:** Jovan (Frontend Developer)

---

## 1. Scope

This document covers the frontend React application for CloudStudy, built as a separate `frontend/` directory using Vite + TypeScript. The implementation includes:

- Complete page routing with authentication guards
- Cognito OAuth2 login flow (Hosted UI redirect + authorization code exchange)
- File upload with drag-and-drop and text paste support
- AI-generated content display (summary, quiz, flashcards, translation)
- Interactive quiz with scoring and flippable flashcards
- Upload history tracking via localStorage (until backend history endpoint exists)
- Mock data fallbacks for development without backend generate/results endpoints

**Out of scope:** Backend API implementation (Branson), Cognito AWS setup (Jia Zen), AWS infrastructure (Week 13).

---

## 2. Tech Stack

| Concern | Choice |
|---------|--------|
| Framework | React 19 + TypeScript |
| Build tool | Vite 8 |
| Routing | react-router-dom v7 |
| HTTP client | Native `fetch` (wrapped in `api/client.ts`) |
| Styling | CSS Modules (`.module.css`) |
| Auth | React Context + Cognito OAuth2 (Authorization Code flow) |
| State management | React `useState` / `useEffect` (no external library) |

**Runtime dependencies:** `react`, `react-dom`, `react-router-dom` — no axios, no Tailwind, no Redux.

---

## 3. File Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.ts              # Dev proxy: /api → http://localhost:5000
├── .env                        # Cognito credentials (gitignored)
├── .env.example                # Template for Cognito env vars
├── tsconfig.json
├── src/
│   ├── main.tsx                # BrowserRouter + AuthProvider + App
│   ├── App.tsx                 # Route definitions
│   ├── index.css               # Global reset + base styles
│   │
│   ├── api/
│   │   ├── client.ts           # Fetch wrapper — attaches Bearer token to all requests
│   │   ├── cognito.ts          # Cognito OAuth2 helpers (login URL, token exchange, JWT decode)
│   │   └── mockData.ts         # Sample quiz/flashcard/summary for dev without backend
│   │
│   ├── types/
│   │   └── index.ts            # UploadResponse, MaterialResult, QuizItem, Flashcard, etc.
│   │
│   ├── context/
│   │   └── AuthContext.tsx      # Auth provider: mock login + real Cognito token handling
│   │
│   ├── components/
│   │   ├── Navbar.tsx           # Top nav bar with auth-aware links
│   │   ├── ProtectedRoute.tsx   # Redirects unauthenticated users to /login
│   │   ├── FileDropZone.tsx     # Drag-and-drop + click-to-browse file input
│   │   ├── FlashCard.tsx        # Flippable card with CSS 3D transform
│   │   └── QuizQuestion.tsx     # Multiple choice with answer checking + feedback
│   │
│   └── pages/
│       ├── LoginPage.tsx        # Cognito redirect OR mock login (auto-detected)
│       ├── CallbackPage.tsx     # Handles Cognito redirect: code → token exchange
│       ├── DashboardPage.tsx    # Welcome, health check, action cards, recent uploads
│       ├── UploadPage.tsx       # File/text upload + generation type selection
│       ├── ResultPage.tsx       # Tabbed view: Summary | Quiz | Flashcards | Translation
│       └── HistoryPage.tsx      # Table of past uploads with "View Results" links
```

---

## 4. Authentication Flow

### Cognito OAuth2 (production)

```
/login → Click "Sign in with AWS Cognito"
   → Redirect to Cognito Hosted UI
   → User authenticates on Cognito
   → Cognito redirects to /callback?code=<authorization_code>
   → CallbackPage exchanges code for tokens (POST /oauth2/token)
   → Tokens stored in localStorage:
       - token (access_token) → attached to all API calls as Bearer header
       - id_token → decoded to extract user email
       - refresh_token → stored for future use
   → Redirect to / (Dashboard)
```

### Mock auth (local dev without Cognito)

When `VITE_COGNITO_DOMAIN` and `VITE_COGNITO_CLIENT_ID` are not set, the login page shows a standard email/password form. Any credentials are accepted and a mock token is stored.

### Cognito Configuration

```env
VITE_COGNITO_DOMAIN=https://us-east-1ss7jhfzsc.auth.us-east-1.amazoncognito.com
VITE_COGNITO_CLIENT_ID=6e19pdbg68cjiurm4b78ukgm6a
VITE_COGNITO_REDIRECT_URI=http://localhost:5173/callback
```

**Prerequisite:** `http://localhost:5173/callback` must be registered as an Allowed Callback URL in the Cognito App Client settings.

---

## 5. Pages

### Login (`/login`)
- If Cognito configured: single "Sign in with AWS Cognito" button → redirects to Hosted UI
- If not configured: email/password form with yellow dev-mode banner
- Auto-redirects to `/` if already authenticated

### Callback (`/callback`)
- Receives `?code=` from Cognito redirect
- Exchanges code for JWT tokens via POST to Cognito `/oauth2/token`
- Shows "Signing you in..." spinner during exchange
- Shows error message if exchange fails
- On success: stores tokens and redirects to `/`

### Dashboard (`/`)
- Welcome message with user email
- Backend health indicator (green/red dot via `GET /api/health`)
- Two action cards: "Upload Material" and "View History"
- Recent uploads section (from localStorage)

### Upload (`/upload`)
- Two modes: file upload (drag-and-drop) or text paste (textarea)
- File validation: allowed types (pdf, png, jpg, jpeg, txt), max 10 MB
- After input: checkboxes to select generation types (Summary, Quiz, Flashcards, Translation)
- Calls `POST /api/upload` → then `POST /api/generate` → navigates to `/result/:id`
- Falls back to mock data if generate endpoint returns 404
- Saves to localStorage history on successful upload

### Result (`/result/:materialId`)
- Tabbed interface — only shows tabs for generated content types
- **Summary tab:** formatted text block
- **Quiz tab:** interactive multiple-choice questions with "Check Answer" button, color-coded feedback (green/red), running score counter
- **Flashcards tab:** grid of flippable cards with CSS 3D transform animation
- **Translation tab:** formatted text block
- Loads from localStorage cache first, then tries `GET /api/results/:id`, then falls back to mock data

### History (`/history`)
- Table with columns: Filename, Generated types, Date, Actions
- "View Results" link navigates to `/result/:id`
- Empty state with link to upload page
- Data from localStorage until backend history endpoint exists

---

## 6. API Integration

All API calls go through `api/client.ts`, which:
- Reads `localStorage.getItem('token')` (the Cognito access_token)
- Attaches `Authorization: Bearer <token>` header to every request
- Throws the parsed error body on non-2xx responses

### Vite Dev Proxy

`vite.config.ts` proxies `/api/*` to `http://localhost:5000`, so the frontend calls `/api/upload` and Vite forwards it to Flask. No CORS issues in development.

### Current endpoint usage

| Frontend function | Backend endpoint | Status |
|-------------------|-----------------|--------|
| `healthCheck()` | `GET /api/health` | Working |
| `uploadFile(file)` | `POST /api/upload` | Working (returns 200 stub) |
| `generateContent(id, types)` | `POST /api/generate` | Not yet — uses mock data |
| `getResults(id)` | `GET /api/results/:id` | Not yet — uses mock data |

---

## 7. Known API Mismatches with Backend Spec

Branson's backend pipeline design (2026-03-29-backend.md) defines API contracts that differ from what the frontend currently expects. These need to be aligned during Week 13 integration:

| Area | Frontend (current) | Backend spec (Branson) | Action needed |
|------|-------------------|----------------------|---------------|
| Upload response | `200` with `{material_id, filename, message}` | `202` with `{material_id, status: "extracting"}` | Update `UploadResponse` type and upload flow |
| Generate endpoint | `POST /api/generate` with `{material_id, types: [...]}` (batch) | `POST /api/generate/<material_id>` with `{type: "summary"}` (one at a time) | Refactor to call generate per type sequentially |
| Generate errors | Generic error handling | `409` (still extracting), `422` (OCR failed) | Add polling/retry for 409, error display for 422 |
| Results shape | `{material_id, filename, summary?, quiz?, flashcards?}` | `{material_id, filename, status, results: {summary: {status, content}, ...}}` | Update `MaterialResult` type and ResultPage parsing |
| Translation | Included as generation type | Deferred — not in backend | Remove from generation options or grey out |
| OCR polling | Not implemented | Frontend should poll `GET /api/results/:id` until `status: "ready"` | Add polling after upload before showing generate options |

---

## 8. How to Run

```bash
cd frontend
cp .env.example .env    # Fill in Cognito values
npm install
npm run dev             # http://localhost:5173
```

For full flow, also start the Flask backend:
```bash
cd backend
python run.py           # http://localhost:5000
```

---

## 9. Verification Checklist

- [ ] `npm run dev` starts without errors on http://localhost:5173
- [ ] Unauthenticated → redirected to `/login`
- [ ] Login with Cognito → redirected to Cognito Hosted UI → callback → Dashboard
- [ ] Dashboard shows green health indicator (if backend running)
- [ ] Upload page: drag-and-drop a PDF → calls `POST /api/upload` → gets `material_id`
- [ ] Result page: shows summary/quiz/flashcards in tabs (mock data if backend not ready)
- [ ] Quiz: select answers, check, see green/red feedback and score
- [ ] Flashcards: click to flip, click again to flip back
- [ ] History page: shows past uploads, "View Results" links work
- [ ] Logout clears session and redirects to Cognito logout
- [ ] `npm run build` succeeds with zero errors
