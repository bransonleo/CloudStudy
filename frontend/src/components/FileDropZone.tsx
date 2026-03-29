import { useState, useRef, type DragEvent } from 'react';
import styles from './FileDropZone.module.css';

const ALLOWED = ['pdf', 'png', 'jpg', 'jpeg', 'txt'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

interface Props {
  onFileSelected: (file: File) => void;
}

export default function FileDropZone({ onFileSelected }: Props) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const [selectedName, setSelectedName] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(file: File): string | null {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED.includes(ext)) {
      return `File type ".${ext}" is not allowed. Allowed: ${ALLOWED.join(', ')}`;
    }
    if (file.size > MAX_SIZE) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: 10 MB`;
    }
    return null;
  }

  function handleFile(file: File) {
    const err = validate(file);
    if (err) {
      setError(err);
      setSelectedName('');
      return;
    }
    setError('');
    setSelectedName(`${file.name} (${(file.size / 1024).toFixed(0)} KB)`);
    onFileSelected(file);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div
      className={`${styles.zone} ${dragging ? styles.active : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.txt"
        onChange={onInputChange}
        hidden
      />
      <p className={styles.label}>
        {selectedName || 'Drag & drop a file here, or click to browse'}
      </p>
      <p className={styles.hint}>Allowed: PDF, PNG, JPG, TXT (max 10 MB)</p>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
