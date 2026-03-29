import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FileDropZone from '../components/FileDropZone';
import { uploadFile, generateContent } from '../api/client';
import { mockResult } from '../api/mockData';
import type { GenerationType, HistoryEntry } from '../types';
import styles from './UploadPage.module.css';

const GENERATION_OPTIONS: { value: GenerationType; label: string }[] = [
  { value: 'summary', label: 'Summary' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'flashcards', label: 'Flashcards' },
  { value: 'translation', label: 'Translation' },
];

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [mode, setMode] = useState<'file' | 'text'>('file');
  const [selectedTypes, setSelectedTypes] = useState<Set<GenerationType>>(new Set(['summary']));
  const [status, setStatus] = useState<'idle' | 'uploading' | 'generating' | 'error'>('idle');
  const [error, setError] = useState('');

  const hasInput = mode === 'file' ? !!file : pastedText.trim().length > 0;

  function toggleType(t: GenerationType) {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  async function handleGenerate() {
    if (!hasInput || selectedTypes.size === 0) return;

    setError('');
    setStatus('uploading');

    try {
      let materialId: string;

      if (mode === 'file' && file) {
        const res = await uploadFile(file);
        materialId = res.material_id;
      } else {
        // For pasted text, create a Blob as a .txt file
        const blob = new Blob([pastedText], { type: 'text/plain' });
        const txtFile = new File([blob], 'pasted-notes.txt', { type: 'text/plain' });
        const res = await uploadFile(txtFile);
        materialId = res.material_id;
      }

      setStatus('generating');

      try {
        const result = await generateContent(materialId, [...selectedTypes]);
        // Store result for the result page
        localStorage.setItem(`result-${materialId}`, JSON.stringify(result));
      } catch {
        // /api/generate not implemented yet — store mock data
        const mock = { ...mockResult, material_id: materialId, filename: file?.name ?? 'pasted-notes.txt' };
        localStorage.setItem(`result-${materialId}`, JSON.stringify(mock));
      }

      // Save to history
      const entry: HistoryEntry = {
        material_id: materialId,
        filename: file?.name ?? 'pasted-notes.txt',
        timestamp: new Date().toISOString(),
        types: [...selectedTypes],
      };
      const history: HistoryEntry[] = JSON.parse(localStorage.getItem('uploadHistory') ?? '[]');
      history.push(entry);
      localStorage.setItem('uploadHistory', JSON.stringify(history));

      navigate(`/result/${materialId}`);
    } catch (err: unknown) {
      setStatus('error');
      const msg = (err && typeof err === 'object' && 'error' in err) ? (err as { error: string }).error : 'Upload failed';
      setError(msg);
    }
  }

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
                />
                {label}
              </label>
            ))}
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button
            className={styles.generateBtn}
            onClick={handleGenerate}
            disabled={selectedTypes.size === 0 || status === 'uploading' || status === 'generating'}
          >
            {status === 'uploading'
              ? 'Uploading...'
              : status === 'generating'
                ? 'Generating...'
                : 'Generate'}
          </button>
        </section>
      )}
    </div>
  );
}
