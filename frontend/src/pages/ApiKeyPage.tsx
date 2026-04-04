import { useState, useEffect } from 'react';
import styles from './ApiKeyPage.module.css';

export default function ApiKeyPage() {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('gemini_api_key');
    if (stored) {
      setApiKey(stored);
      setHasKey(true);
    }
  }, []);

  function handleSave() {
    if (!apiKey.trim()) return;
    localStorage.setItem('gemini_api_key', apiKey.trim());
    setHasKey(true);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleRemove() {
    localStorage.removeItem('gemini_api_key');
    setApiKey('');
    setHasKey(false);
  }

  return (
    <div className={styles.container}>
      <h1>API Key Settings</h1>

      <div className={styles.card}>
        <h2>Gemini API Key</h2>
        <p className={styles.description}>
          Enter your Google Gemini API key to generate summaries, quizzes, and flashcards.
          Your key is stored locally in your browser and sent securely with each request.
        </p>

        <p className={styles.help}>
          Don't have a key?{' '}
          <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">
            Get one free from Google AI Studio
          </a>
        </p>

        <div className={styles.inputRow}>
          <input
            className={styles.keyInput}
            type="password"
            placeholder="AIzaSy..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <button className={styles.saveBtn} onClick={handleSave} disabled={!apiKey.trim()}>
            {hasKey ? 'Update' : 'Save'}
          </button>
          {hasKey && (
            <button className={styles.removeBtn} onClick={handleRemove}>
              Remove
            </button>
          )}
        </div>

        {saved && <p className={styles.success}>API key saved successfully.</p>}

        {hasKey && !saved && (
          <p className={styles.status}>API key is set and ready to use.</p>
        )}
      </div>
    </div>
  );
}
