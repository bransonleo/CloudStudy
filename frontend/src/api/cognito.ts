const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const REDIRECT_URI = import.meta.env.VITE_COGNITO_REDIRECT_URI || 'http://localhost:5173/callback';

// Full Cognito domain URL (e.g., https://us-east-1ss7jhfzsc.auth.us-east-1.amazoncognito.com)
const BASE_URL = (import.meta.env.VITE_COGNITO_DOMAIN || '').replace(/\/+$/, '');

/**
 * Build the Cognito Hosted UI login URL.
 * Redirects the user to Cognito for authentication.
 */
export function getCognitoLoginUrl(): string {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: 'openid email profile',
  });
  return `${BASE_URL}/oauth2/authorize?${params.toString()}`;
}

/**
 * Build the Cognito logout URL.
 * Redirects the user to Cognito to clear the session, then back to login.
 */
export function getCognitoLogoutUrl(): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: REDIRECT_URI.replace('/callback', '/login'),
  });
  return `${BASE_URL}/logout?${params.toString()}`;
}

/**
 * Exchange an authorization code for JWT tokens.
 * POST to Cognito's /oauth2/token endpoint.
 */
export async function exchangeCodeForTokens(code: string): Promise<{
  id_token: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
}> {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    code,
  });

  const res = await fetch(`${BASE_URL}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Token exchange failed');
  }

  return res.json();
}

/**
 * Decode a JWT token payload (without verification — verification is done server-side).
 * Used to extract user info like email from the id_token.
 */
export function decodeJwtPayload(token: string): Record<string, unknown> {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const json = decodeURIComponent(
    atob(base64)
      .split('')
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
  );
  return JSON.parse(json);
}

/**
 * Check if Cognito is configured (env vars are set).
 * If not, the app falls back to mock auth for local development.
 */
export function isCognitoConfigured(): boolean {
  return !!(BASE_URL && CLIENT_ID);
}
