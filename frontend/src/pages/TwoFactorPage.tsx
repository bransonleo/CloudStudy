import { useState, useEffect } from 'react';
import { CognitoUserPool, CognitoUser, CognitoUserSession, CognitoAccessToken, CognitoIdToken, CognitoRefreshToken } from 'amazon-cognito-identity-js';
import { QRCodeSVG } from 'qrcode.react';
import { useAuth } from '../context/AuthContext';
import styles from './TwoFactorPage.module.css';

const userPool = new CognitoUserPool({
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
  ClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
});

type Step = 'loading' | 'idle' | 'scan' | 'verify' | 'done' | 'error';

function getCognitoUser(): CognitoUser | null {
  const email = localStorage.getItem('userEmail');
  if (!email) return null;

  const user = new CognitoUser({ Username: email, Pool: userPool });

  // Restore the session so Cognito SDK can make authenticated calls
  const accessToken = localStorage.getItem('token');
  const idToken = localStorage.getItem('id_token');
  const refreshToken = localStorage.getItem('refresh_token');

  if (accessToken && idToken && refreshToken) {
    const session = new CognitoUserSession({
      AccessToken: new CognitoAccessToken({ AccessToken: accessToken }),
      IdToken: new CognitoIdToken({ IdToken: idToken }),
      RefreshToken: new CognitoRefreshToken({ RefreshToken: refreshToken }),
    });
    user.setSignInUserSession(session);
  }

  return user;
}

export default function TwoFactorPage() {
  const { userEmail } = useAuth();
  const [step, setStep] = useState<Step>('loading');
  const [secret, setSecret] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');

  // Check if 2FA is already enabled on mount
  useEffect(() => {
    const user = getCognitoUser();
    if (!user) {
      setStep('idle');
      return;
    }

    user.getMFAOptions((err, mfaOptions) => {
      if (err) {
        // getMFAOptions may not work for TOTP; fall back to getUser
        user.getUserData((userErr, data) => {
          if (userErr) {
            setStep('idle');
            return;
          }
          const mfaSettings = data?.UserMFASettingList ?? [];
          if (mfaSettings.includes('SOFTWARE_TOKEN_MFA')) {
            setStep('done');
          } else {
            setStep('idle');
          }
        });
        return;
      }
      if (mfaOptions && mfaOptions.length > 0) {
        setStep('done');
      } else {
        // Double-check via getUser for TOTP
        user.getUserData((_err2, data) => {
          const mfaSettings = data?.UserMFASettingList ?? [];
          if (mfaSettings.includes('SOFTWARE_TOKEN_MFA')) {
            setStep('done');
          } else {
            setStep('idle');
          }
        });
      }
    });
  }, []);

  const otpauthUrl = secret
    ? `otpauth://totp/CloudStudy:${userEmail}?secret=${secret}&issuer=CloudStudy`
    : '';

  function handleEnable() {
    setError('');
    const user = getCognitoUser();
    if (!user) {
      setError('No authenticated user found. Please log in again.');
      return;
    }

    user.associateSoftwareToken({
      associateSecretCode: (secretCode: string) => {
        setSecret(secretCode);
        setStep('scan');
      },
      onFailure: (err: Error) => {
        setError(err.message || 'Failed to start TOTP setup.');
        setStep('error');
      },
    });
  }

  function handleVerify() {
    if (code.length !== 6) {
      setError('Please enter a 6-digit code.');
      return;
    }

    setError('');
    const user = getCognitoUser();
    if (!user) {
      setError('No authenticated user found.');
      return;
    }

    user.verifySoftwareToken(code, 'CloudStudy', {
      onSuccess: () => {
        // Set TOTP as the preferred MFA method
        user.setUserMfaPreference(null, { PreferredMfa: true, Enabled: true }, (err) => {
          if (err) {
            console.error('Failed to set MFA preference:', err);
          }
        });
        setStep('done');
      },
      onFailure: (err: Error) => {
        setError(err.message || 'Invalid code. Please try again.');
      },
    });
  }

  return (
    <div className={styles.container}>
      <h1>Two-Factor Authentication</h1>

      {step === 'loading' && (
        <div className={styles.card}>
          <p className={styles.description}>Checking 2FA status...</p>
        </div>
      )}

      {step === 'idle' && (
        <div className={styles.card}>
          <p className={styles.description}>
            Add an extra layer of security to your account by enabling two-factor authentication
            with Google Authenticator or any TOTP-compatible app.
          </p>
          <button className={styles.enableBtn} onClick={handleEnable}>
            Enable 2FA
          </button>
        </div>
      )}

      {step === 'scan' && (
        <div className={styles.card}>
          <h2>Step 1: Scan QR Code</h2>
          <p className={styles.description}>
            Open Google Authenticator on your phone and scan this QR code.
          </p>
          <div className={styles.qrWrapper}>
            <QRCodeSVG value={otpauthUrl} size={200} />
          </div>
          <p className={styles.secretText}>
            Can't scan? Enter this code manually: <code className={styles.code}>{secret}</code>
          </p>
          <button className={styles.enableBtn} onClick={() => setStep('verify')}>
            Next
          </button>
        </div>
      )}

      {step === 'verify' && (
        <div className={styles.card}>
          <h2>Step 2: Enter Verification Code</h2>
          <p className={styles.description}>
            Enter the 6-digit code shown in your authenticator app to confirm setup.
          </p>
          <input
            className={styles.codeInput}
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            autoFocus
          />
          <button
            className={styles.enableBtn}
            onClick={handleVerify}
            disabled={code.length !== 6}
          >
            Verify & Enable
          </button>
        </div>
      )}

      {step === 'done' && (
        <div className={styles.card}>
          <div className={styles.successIcon}>&#10003;</div>
          <h2>2FA Enabled</h2>
          <p className={styles.description}>
            Two-factor authentication is now active on your account.
            You'll need your authenticator app each time you log in.
          </p>
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
