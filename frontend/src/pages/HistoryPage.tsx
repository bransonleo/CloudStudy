import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { HistoryEntry } from '../types';
import styles from './HistoryPage.module.css';

export default function HistoryPage() {
  const [entries] = useState<HistoryEntry[]>(() => {
    const saved = localStorage.getItem('uploadHistory');
    if (!saved) return [];
    const all: HistoryEntry[] = JSON.parse(saved);
    return all.slice().reverse();
  });

  return (
    <div>
      <h1>Upload History</h1>

      {entries.length === 0 ? (
        <div className={styles.empty}>
          <p>No uploads yet.</p>
          <Link to="/upload">Upload your first study material</Link>
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Generated</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.material_id}>
                <td>{entry.filename}</td>
                <td>{entry.types.join(', ')}</td>
                <td>{new Date(entry.timestamp).toLocaleString()}</td>
                <td>
                  <Link to={`/result/${entry.material_id}`} className={styles.viewLink}>
                    View Results
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
