import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FileDropZone from '../components/FileDropZone';
import { uploadFile, generateContent, getResults } from '../api/client';
import type { GenerationType, HistoryEntry } from '../types';
import styles from './UploadPage.module.css';

const GENERATION_OPTIONS: { value: GenerationType; label: string }[] = [
  { value: 'summary', label: 'Summary' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'flashcards', label: 'Flashcards' },
];

type Status = 'idle' | 'uploading' | 'extracting' | 'generating' | 'error';

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [mode, setMode] = useState<'file' | 'text'>('file');
  const [selectedTypes, setSelectedTypes] = useState<Set<GenerationType>>(new Set(['summary']));
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const hasInput = mode === 'file' ? !!file : pastedText.trim().length > 0;

  function toggleType(t: GenerationType) {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function runGenerate(materialId: string, filename: string) {
    setStatus('generating');
    for (const type of selectedTypes) {
      await generateContent(materialId, type);
    }

    // Save to history
    const entry: HistoryEntry = {
      material_id: materialId,
      filename,
      timestamp: new Date().toISOString(),
      types: [...selectedTypes],
    };
    const history: HistoryEntry[] = JSON.parse(localStorage.getItem('uploadHistory') ?? '[]');
    history.push(entry);
    localStorage.setItem('uploadHistory', JSON.stringify(history));

    navigate(`/result/${materialId}`);
  }

  async function handleGenerate() {
    if (!hasInput || selectedTypes.size === 0) return;

    setError('');
    setStatus('uploading');

    try {
      let materialId: string;
      let filename: string;

      if (mode === 'file' && file) {
        const res = await uploadFile(file);
        materialId = res.material_id;
        filename = file.name;
      } else {
        const blob = new Blob([pastedText], { type: 'text/plain' });
        const txtFile = new File([blob], 'pasted-notes.txt', { type: 'text/plain' });
        const res = await uploadFile(txtFile);
        materialId = res.material_id;
        filename = 'pasted-notes.txt';
      }

      // Backend returns 202 — OCR is running in background, poll until ready
      setStatus('extracting');

      await new Promise<void>((resolve, reject) => {
        pollRef.current = setInterval(async () => {
          try {
            const data = await getResults(materialId);
            if (data.status === 'ready') {
              stopPolling();
              resolve();
            } else if (data.status === 'error') {
              stopPolling();
              reject(new Error(data.error_message ?? 'Text extraction failed'));
            }
            // status === 'extracting' → keep polling
          } catch {
            stopPolling();
            reject(new Error('Failed to check processing status'));
          }
        }, 2000);
      });

      await runGenerate(materialId, filename);
    } catch (err: unknown) {
      stopPolling();
      setStatus('error');
      const msg = (err instanceof Error)
        ? err.message
        : (err && typeof err === 'object' && 'error' in err)
          ? (err as { error: string }).error
          : 'Something went wrong';
      setError(msg);
    }
  }

  const buttonLabel = {
    idle: 'Generate',
    uploading: 'Uploading...',
    extracting: 'Extracting text...',
    generating: 'Generating...',
    error: 'Generate',
  }[status];

  const isBusy = status === 'uploading' || status === 'extracting' || status === 'generating';

  return (
    <div>
      <h1>Upload Study Material</h1>

      <div className={styles.modeTabs}>
        <button
          className={`${styles.tab} ${mode === 'file' ? styles.activeTab : ''}`}
          onClick={() => setMode('file')}
        >
          Upload File
        </button>
        <button
          className={`${styles.tab} ${mode === 'text' ? styles.activeTab : ''}`}
          onClick={() => setMode('text')}
        >
          Paste Text
        </button>
      </div>

      {mode === 'file' ? (
        <FileDropZone onFileSelected={setFile} />
      ) : (
        <textarea
          className={styles.textarea}
          placeholder="Paste your study notes here..."
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
          rows={8}
        />
      )}

      {hasInput && (
        <section className={styles.options}>
          <h2>What would you like to generate?</h2>
          <div className={styles.checks}>
            {GENERATION_OPTIONS.map(({ value, label }) => (
              <label key={value} className={styles.checkLabel}>
                <input
                  type="checkbox"
                  checked={selectedTypes.has(value)}
                  onChange={() => toggleType(value)}
                  disabled={isBusy}
                />
                {label}
              </label>
            ))}
          </div>

          {status === 'extracting' && (
            <p className={styles.info}>Extracting text from your file, this may take a moment...</p>
          )}

          {error && <p className={styles.error}>{error}</p>}

          <button
            className={styles.generateBtn}
            onClick={handleGenerate}
            disabled={selectedTypes.size === 0 || isBusy}
          >
            {buttonLabel}
          </button>
        </section>
      )}
    </div>
  );
}
