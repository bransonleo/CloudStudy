import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getResults } from '../api/client';
import { mockResult } from '../api/mockData';
import FlashCard from '../components/FlashCard';
import QuizQuestion from '../components/QuizQuestion';
import type { MaterialResult } from '../types';
import styles from './ResultPage.module.css';

type Tab = 'summary' | 'quiz' | 'flashcards' | 'translation';

export default function ResultPage() {
  const { materialId } = useParams<{ materialId: string }>();
  const [result, setResult] = useState<MaterialResult | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!materialId) return;

    // Try localStorage first (saved during upload flow)
    const cached = localStorage.getItem(`result-${materialId}`);
    if (cached) {
      setResult(JSON.parse(cached));
      setLoading(false);
      return;
    }

    // Try API, fall back to mock
    getResults(materialId)
      .then(setResult)
      .catch(() => setResult({ ...mockResult, material_id: materialId }))
      .finally(() => setLoading(false));
  }, [materialId]);

  if (loading) return <p>Loading results...</p>;
  if (!result) return <p>No results found.</p>;

  const tabs: { key: Tab; label: string; available: boolean }[] = [
    { key: 'summary', label: 'Summary', available: !!result.summary },
    { key: 'quiz', label: 'Quiz', available: !!result.quiz?.length },
    { key: 'flashcards', label: 'Flashcards', available: !!result.flashcards?.length },
    { key: 'translation', label: 'Translation', available: !!result.translation },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  return (
    <div>
      <h1>Results: {result.filename}</h1>

      <div className={styles.tabs}>
        {availableTabs.map((t) => (
          <button
            key={t.key}
            className={`${styles.tab} ${activeTab === t.key ? styles.activeTab : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {activeTab === 'summary' && result.summary && (
          <div className={styles.summaryText}>{result.summary}</div>
        )}

        {activeTab === 'quiz' && result.quiz && (
          <div>
            {result.quiz.map((q, i) => (
              <QuizQuestion
                key={i}
                questionNumber={i + 1}
                question={q.question}
                options={q.options}
                correctIndex={q.correct_index}
                onAnswer={(correct) => {
                  setAnswered((a) => a + 1);
                  if (correct) setScore((s) => s + 1);
                }}
              />
            ))}
            {answered > 0 && (
              <p className={styles.score}>
                Score: {score} / {result.quiz.length}
                {answered === result.quiz.length && (
                  <span> — {score === result.quiz.length ? 'Perfect!' : 'Keep studying!'}</span>
                )}
              </p>
            )}
          </div>
        )}

        {activeTab === 'flashcards' && result.flashcards && (
          <div className={styles.flashcardGrid}>
            {result.flashcards.map((fc, i) => (
              <FlashCard key={i} front={fc.front} back={fc.back} />
            ))}
          </div>
        )}

        {activeTab === 'translation' && result.translation && (
          <div className={styles.summaryText}>{result.translation}</div>
        )}
      </div>
    </div>
  );
}
