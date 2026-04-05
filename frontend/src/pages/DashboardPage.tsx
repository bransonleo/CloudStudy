import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { healthCheck } from '../api/client';
import type { HistoryEntry } from '../types';
import styles from './DashboardPage.module.css';

export default function DashboardPage() {
  const { userEmail } = useAuth();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [recent] = useState<HistoryEntry[]>(() => {
    const saved = localStorage.getItem('uploadHistory');
    if (!saved) return [];
    const all: HistoryEntry[] = JSON.parse(saved);
    return all.slice(-5).reverse();
  });

  useEffect(() => {
    healthCheck()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  return (
    <div>
      <h1 className={styles.heading}>
        Welcome{userEmail ? `, ${userEmail}` : ''}
      </h1>

      <div className={styles.status}>
        <span
          className={styles.dot}
          style={{ background: backendOk === null ? '#94a3b8' : backendOk ? '#22c55e' : '#ef4444' }}
        />
        Backend: {backendOk === null ? 'checking...' : backendOk ? 'connected' : 'unreachable'}
      </div>

      <div className={styles.cards}>
        <Link to="/upload" className={styles.card}>
          <h2>Upload Material</h2>
          <p>Upload a PDF, image, or text file and generate study aids with AI.</p>
        </Link>
        <Link to="/history" className={styles.card}>
          <h2>View History</h2>
          <p>Browse your previously uploaded materials and generated results.</p>
        </Link>
      </div>

      {recent.length > 0 && (
        <section className={styles.recent}>
          <h2>Recent Uploads</h2>
          <ul className={styles.list}>
            {recent.map((entry) => (
              <li key={entry.material_id}>
                <Link to={`/result/${entry.material_id}`}>{entry.filename}</Link>
                <span className={styles.date}>
                  {new Date(entry.timestamp).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
