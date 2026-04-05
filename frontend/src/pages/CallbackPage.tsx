import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { exchangeCodeForTokens } from '../api/cognito';
import styles from './CallbackPage.module.css';

export default function CallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setTokens } = useAuth();
  const attempted = useRef(false); // prevents React StrictMode double-invocation
  const code = searchParams.get('code');
  const errorParam = searchParams.get('error');
  const [error, setError] = useState(
    errorParam
      ? `Cognito error: ${errorParam}`
      : !code
        ? 'No authorization code received from Cognito.'
        : ''
  );

  useEffect(() => {
    if (attempted.current || error || !code) return;
    attempted.current = true;

    exchangeCodeForTokens(code)
      .then((tokens) => {
        setTokens(tokens.id_token, tokens.access_token, tokens.refresh_token);
        navigate('/', { replace: true });
      })
      .catch((err) => {
        setError(err.message || 'Failed to exchange code for tokens.');
      });
  }, [code, error, setTokens, navigate]);

  if (error) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.card}>
          <h2>Login Failed</h2>
          <p className={styles.error}>{error}</p>
          <a href="/login" className={styles.link}>Back to Login</a>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h2>Signing you in...</h2>
        <p>Exchanging credentials with Cognito. Please wait.</p>
      </div>
    </div>
  );
}
