# Frontend Implementation — CloudStudy

**Date:** 2026-04-04 (Updated)
**Author:** Jovan (Frontend Developer)

---

## 1. Scope

This document covers the frontend React application for CloudStudy, built as a separate `frontend/` directory using Vite + TypeScript. The implementation includes:

- Complete page routing with authentication guards
- Cognito OAuth2 login flow (Hosted UI redirect + authorization code exchange)
- File upload with drag-and-drop and text paste support
- AI-generated content display (summary, quiz, flashcards)
- Interactive quiz with scoring and explanation feedback
- NotebookLM-style single-card flashcard viewer with navigation
- "Generate more" — add content types to existing uploads without re-uploading
- Auto-tab selection — automatically shows available content when only one type exists
- Upload history tracking via localStorage
- Two-Factor Authentication (TOTP) enrollment via Google Authenticator
- Mock data fallbacks for development without backend generate/results endpoints

**Out of scope:** Backend API implementation (Branson), Cognito AWS setup (Jia Zen), AWS infrastructure.

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
| 2FA / TOTP | `amazon-cognito-identity-js` + `qrcode.react` |
| State management | React `useState` / `useEffect` (no external library) |

**Runtime dependencies:** `react`, `react-dom`, `react-router-dom`, `amazon-cognito-identity-js`, `qrcode.react`.

---

## 3. File Structure

```
frontend/
├── index.html                  # Global polyfill for `global` (required by cognito-identity-js)
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
│   │   └── index.ts            # UploadResponse, BackendMaterial, QuizItem, Flashcard, HistoryEntry, etc.
│   │
│   ├── context/
│   │   └── AuthContext.tsx      # Auth provider: mock login + real Cognito token handling
│   │
│   ├── components/
│   │   ├── Navbar.tsx           # Top nav bar with auth-aware links + 2FA settings link
│   │   ├── ProtectedRoute.tsx   # Redirects unauthenticated users to /login
│   │   ├── FileDropZone.tsx     # Drag-and-drop + click-to-browse file input
│   │   ├── FlashCard.tsx        # Single-card viewer with prev/next navigation (NotebookLM-style)
│   │   └── QuizQuestion.tsx     # Multiple choice with answer checking + explanation feedback
│   │
│   └── pages/
│       ├── LoginPage.tsx        # Cognito redirect OR mock login (auto-detected)
│       ├── CallbackPage.tsx     # Handles Cognito redirect: code → token exchange
│       ├── DashboardPage.tsx    # Welcome, health check, action cards, recent uploads
│       ├── UploadPage.tsx       # File/text upload + generation type selection
│       ├── ResultPage.tsx       # Tabbed view: Summary | Quiz | Flashcards + "Generate more"
│       ├── HistoryPage.tsx      # Table of past uploads with "View Results" links
│       └── TwoFactorPage.tsx    # TOTP 2FA enrollment: QR code scan + verification
```

---

## 4. Authentication Flow

### Cognito OAuth2 (production)

```
/login → Click "Sign in with AWS Cognito"
   → Redirect to Cognito Hosted UI
   → User authenticates on Cognito (+ MFA challenge if 2FA enabled)
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

### Two-Factor Authentication (TOTP)

```
/settings/2fa → Click "Enable 2FA"
   → Cognito SDK generates TOTP secret
   → QR code displayed (otpauth:// URL via qrcode.react)
   → User scans with Google Authenticator
   → User enters 6-digit code to verify
   → TOTP linked to account, set as preferred MFA method
   → Next login: Cognito Hosted UI prompts for TOTP code automatically
```

**Note:** `index.html` includes a `global = window` polyfill because `amazon-cognito-identity-js` expects the Node.js `global` variable, which does not exist in browser ESM environments.

### Cognito Configuration

```env
VITE_COGNITO_USER_POOL_ID=us-east-1_Ss7jHFZSC
VITE_COGNITO_CLIENT_ID=7oiatn9dtru73j9vrl08896fv4
VITE_COGNITO_DOMAIN=https://us-east-1ss7jhfzsc.auth.us-east-1.amazoncognito.com
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
- After input: checkboxes to select generation types (Summary, Quiz, Flashcards)
- Upload flow: `POST /api/upload` (202) → poll `GET /api/results/:id` until `status: "ready"` → `POST /api/generate/:id` per type → navigate to `/result/:id`
- Saves to localStorage history on successful upload

### Result (`/result/:materialId`)
- **Auto-tab selection** — automatically selects the first available tab (no blank screen if only Quiz was generated)
- **Generate more** — bar at top shows checkboxes for content types not yet generated; generate without re-uploading
- **Summary tab:** title, key points list, and summary text
- **Quiz tab:** interactive multiple-choice questions with color-coded feedback (green/red), explanation text, and running score counter
- **Flashcards tab:** NotebookLM-style single-card viewer — dark gradient card, click to flip (question ↔ answer), prev/next navigation arrows, card counter (e.g. "1 / 45")
- Falls back to mock data if backend not available

### History (`/history`)
- Table with columns: Filename, Generated types, Date, Actions
- "View Results" link navigates to `/result/:id`
- Generated types column updates when new types are added via "Generate more"
- Empty state with link to upload page
- Data from localStorage

### Two-Factor Auth (`/settings/2fa`)
- 3-step enrollment flow: Enable → Scan QR → Verify code
- Uses `amazon-cognito-identity-js` to call Cognito `associateSoftwareToken` and `verifySoftwareToken`
- QR code rendered via `qrcode.react` (SVG)
- Manual secret code shown as fallback if QR scanning not possible
- Sets TOTP as preferred MFA method on successful verification
- Accessible via "2FA" link in navbar (next to logout button)

---

## 6. API Integration

All API calls go through `api/client.ts`, which:
- Reads `localStorage.getItem('token')` (the Cognito access_token)
- Attaches `Authorization: Bearer <token>` header to every request
- Throws the parsed error body on non-2xx responses

### Vite Dev Proxy

`vite.config.ts` proxies `/api/*` to `http://localhost:5000`, so the frontend calls `/api/upload` and Vite forwards it to Flask. No CORS issues in development.

### Endpoint usage

| Frontend function | Backend endpoint | Status |
|-------------------|-----------------|--------|
| `healthCheck()` | `GET /api/health` | Working |
| `uploadFile(file)` | `POST /api/upload` | Working (returns 202) |
| `generateContent(id, type)` | `POST /api/generate/<material_id>` | Working (one type per call) |
| `getResults(id)` | `GET /api/results/<material_id>` | Working |

---

## 7. Recent Changes (April 2026)

| Change | Description |
|--------|-------------|
| Flashcard redesign | Replaced grid of small flip-cards with a single full-width NotebookLM-style card viewer with navigation arrows |
| Generate more | Result page shows checkboxes for missing content types — generate without re-uploading |
| Auto-tab selection | Result page auto-selects the first available tab instead of defaulting to Summary |
| Increased flashcards | Backend prompt updated to generate 30+ flashcards per material |
| 2FA page | New `/settings/2fa` page for TOTP enrollment with QR code scanning |
| Global polyfill | `index.html` includes `global = window` polyfill for `amazon-cognito-identity-js` compatibility |
| History type sync | History entries update their "Generated" column when new types are added via "Generate more" |

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
- [ ] Upload page: drag-and-drop a PDF → calls `POST /api/upload` → polls until ready → generates content
- [ ] Result page: shows summary/quiz/flashcards in tabs
- [ ] Result page: auto-selects available tab when only one type generated
- [ ] Result page: "Generate more" bar lets you add missing content types
- [ ] Quiz: select answers, see green/red feedback, explanation, and score
- [ ] Flashcards: single-card view, click to flip, arrow keys to navigate
- [ ] History page: shows past uploads, generated types update after "Generate more"
- [ ] 2FA page: enable 2FA → scan QR → verify code → success
- [ ] Logout clears session and redirects to Cognito logout
- [ ] `npm run build` succeeds with zero errors
