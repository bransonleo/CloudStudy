import { useState, type FormEvent } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getCognitoLoginUrl, isCognitoConfigured } from '../api/cognito';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const { isAuthenticated, loginMock } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  if (isAuthenticated) return <Navigate to="/" replace />;

  const cognitoReady = isCognitoConfigured();

  // Cognito flow: redirect to Hosted UI
  const handleCognitoLogin = () => {
    window.location.href = getCognitoLoginUrl();
  };

  // Mock flow: for local dev without Cognito
  const handleMockSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    loginMock(email);
    navigate('/');
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h1 className={styles.title}>Welcome to CloudStudy</h1>
        <p className={styles.subtitle}>Sign in to continue</p>

        {cognitoReady ? (
          <>
            <button className={styles.btn} onClick={handleCognitoLogin}>
              Sign in with AWS Cognito
            </button>
            <p className={styles.hint}>You will be redirected to the login page</p>
          </>
        ) : (
          <form onSubmit={handleMockSubmit}>
            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.devBanner}>
              Dev mode — Cognito not configured. Any credentials will work.
            </div>

            <label className={styles.label}>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={styles.input}
                placeholder="you@example.com"
                autoFocus
              />
            </label>

            <label className={styles.label}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={styles.input}
                placeholder="Enter your password"
              />
            </label>

            <button type="submit" className={styles.btn}>Sign In</button>
          </form>
        )}
      </div>
    </div>
  );
}
