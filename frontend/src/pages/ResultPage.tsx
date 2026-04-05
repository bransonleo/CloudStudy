import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getResults, generateContent } from '../api/client';
import { mockMaterial } from '../api/mockData';
import FlashCard from '../components/FlashCard';
import QuizQuestion from '../components/QuizQuestion';
import type { BackendMaterial, SummaryContent, QuizContent, FlashcardsContent, GenerationType } from '../types';
import styles from './ResultPage.module.css';

type Tab = 'summary' | 'quiz' | 'flashcards';

const ALL_TYPES: { value: GenerationType; label: string }[] = [
  { value: 'summary', label: 'Summary' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'flashcards', label: 'Flashcards' },
];

export default function ResultPage() {
  const { materialId } = useParams<{ materialId: string }>();
  const [material, setMaterial] = useState<BackendMaterial | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [loading, setLoading] = useState(true);
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [genTypes, setGenTypes] = useState<Set<GenerationType>>(new Set());
  const [generating, setGenerating] = useState(false);

  const fetchResults = useCallback(() => {
    if (!materialId) return;
    getResults(materialId)
      .then(setMaterial)
      .catch(() => setMaterial({ ...mockMaterial, material_id: materialId }))
      .finally(() => setLoading(false));
  }, [materialId]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

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
  const missingTypes = ALL_TYPES.filter((t) => material.results[t.value].status !== 'done');

  // Auto-select first available tab if current tab has no content
  const effectiveTab = availableTabs.some((t) => t.key === activeTab)
    ? activeTab
    : availableTabs[0]?.key ?? 'summary';

  const summaryContent = material.results.summary.content as SummaryContent | undefined;
  const quizContent = material.results.quiz.content as QuizContent | undefined;
  const flashcardsContent = material.results.flashcards.content as FlashcardsContent | undefined;

  function toggleGenType(t: GenerationType) {
    setGenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  async function handleGenerateMore() {
    if (!materialId || genTypes.size === 0) return;
    setGenerating(true);
    try {
      for (const type of genTypes) {
        await generateContent(materialId, type);
      }
      // Update history entry with new types
      const history: { material_id: string; types: string[] }[] = JSON.parse(
        localStorage.getItem('uploadHistory') ?? '[]'
      );
      const entry = history.find((h) => h.material_id === materialId);
      if (entry) {
        const typeSet = new Set(entry.types);
        for (const t of genTypes) typeSet.add(t);
        entry.types = [...typeSet];
        localStorage.setItem('uploadHistory', JSON.stringify(history));
      }

      setGenTypes(new Set());
      // Refresh results to show new content
      const updated = await getResults(materialId);
      setMaterial(updated);
    } catch (err) {
      console.error('Generate more failed:', err);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <h1>Results: {material.filename}</h1>

      {missingTypes.length > 0 && (
        <div className={styles.generateMore}>
          <span className={styles.generateMoreLabel}>Generate more:</span>
          <div className={styles.generateMoreChecks}>
            {missingTypes.map(({ value, label }) => (
              <label key={value} className={styles.generateMoreCheck}>
                <input
                  type="checkbox"
                  checked={genTypes.has(value)}
                  onChange={() => toggleGenType(value)}
                  disabled={generating}
                />
                {label}
              </label>
            ))}
          </div>
          <button
            className={styles.generateMoreBtn}
            onClick={handleGenerateMore}
            disabled={genTypes.size === 0 || generating}
          >
            {generating ? 'Generating...' : 'Generate'}
          </button>
        </div>
      )}

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
