import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getResults } from '../api/client';
import { mockMaterial } from '../api/mockData';
import FlashCard from '../components/FlashCard';
import QuizQuestion from '../components/QuizQuestion';
import type { BackendMaterial, SummaryContent, QuizContent, FlashcardsContent } from '../types';
import styles from './ResultPage.module.css';

type Tab = 'summary' | 'quiz' | 'flashcards';

export default function ResultPage() {
  const { materialId } = useParams<{ materialId: string }>();
  const [material, setMaterial] = useState<BackendMaterial | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [loading, setLoading] = useState(true);
  const [flashcardIndex, setFlashcardIndex] = useState(0);

  useEffect(() => {
    if (!materialId) return;

    getResults(materialId)
      .then(setMaterial)
      .catch(() => setMaterial({ ...mockMaterial, material_id: materialId }))
      .finally(() => setLoading(false));
  }, [materialId]);

  if (loading) return <p>Loading results...</p>;
  if (!material) return <p>No results found.</p>;

  if (material.status === 'extracting') {
    return (
      <div>
        <h1>{material.filename}</h1>
        <p>Still extracting text from your file. Please check back shortly.</p>
      </div>
    );
  }

  if (material.status === 'error') {
    return (
      <div>
        <h1>{material.filename}</h1>
        <p className={styles.errorMsg}>
          Processing failed: {material.error_message ?? 'Unknown error'}
        </p>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'summary', label: 'Summary' },
    { key: 'quiz', label: 'Quiz' },
    { key: 'flashcards', label: 'Flashcards' },
  ];

  const availableTabs = tabs.filter((t) => material.results[t.key].status === 'done');

  // Auto-select first available tab if current tab has no content
  const effectiveTab = availableTabs.some((t) => t.key === activeTab)
    ? activeTab
    : availableTabs[0]?.key ?? 'summary';

  const summaryContent = material.results.summary.content as SummaryContent | undefined;
  const quizContent = material.results.quiz.content as QuizContent | undefined;
  const flashcardsContent = material.results.flashcards.content as FlashcardsContent | undefined;

  return (
    <div>
      <h1>Results: {material.filename}</h1>

      {availableTabs.length === 0 ? (
        <p>No content has been generated yet.</p>
      ) : (
        <>
          <div className={styles.tabs}>
            {availableTabs.map((t) => (
              <button
                key={t.key}
                className={`${styles.tab} ${effectiveTab === t.key ? styles.activeTab : ''}`}
                onClick={() => setActiveTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className={styles.content}>
            {effectiveTab === 'summary' && summaryContent && (
              <div className={styles.summaryBox}>
                <h2>{summaryContent.title}</h2>
                {summaryContent.key_points.length > 0 && (
                  <ul className={styles.keyPoints}>
                    {summaryContent.key_points.map((pt, i) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                )}
                <p className={styles.summaryText}>{summaryContent.summary}</p>
              </div>
            )}

            {effectiveTab === 'quiz' && quizContent && (
              <div>
                {quizContent.questions.map((q, i) => (
                  <QuizQuestion
                    key={i}
                    questionNumber={i + 1}
                    question={q.question}
                    options={q.options}
                    correctIndex={q.correct_index}
                    explanation={q.explanation}
                    onAnswer={(correct) => {
                      setAnswered((a) => a + 1);
                      if (correct) setScore((s) => s + 1);
                    }}
                  />
                ))}
                {answered > 0 && (
                  <p className={styles.score}>
                    Score: {score} / {quizContent.questions.length}
                    {answered === quizContent.questions.length && (
                      <span> — {score === quizContent.questions.length ? 'Perfect!' : 'Keep studying!'}</span>
                    )}
                  </p>
                )}
              </div>
            )}

            {effectiveTab === 'flashcards' && flashcardsContent && (
              <div className={styles.flashcardSingle}>
                <FlashCard
                  key={flashcardIndex}
                  front={flashcardsContent.flashcards[flashcardIndex].front}
                  back={flashcardsContent.flashcards[flashcardIndex].back}
                  index={flashcardIndex}
                  total={flashcardsContent.flashcards.length}
                  onNext={() => setFlashcardIndex((i) => Math.min(i + 1, flashcardsContent.flashcards.length - 1))}
                  onPrev={() => setFlashcardIndex((i) => Math.max(i - 1, 0))}
                />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
