import { useState } from 'react';
import styles from './QuizQuestion.module.css';

interface Props {
  questionNumber: number;
  question: string;
  options: string[];
  correctIndex: number;
  onAnswer: (correct: boolean) => void;
}

export default function QuizQuestion({ questionNumber, question, options, correctIndex, onAnswer }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit() {
    if (selected === null) return;
    setSubmitted(true);
    onAnswer(selected === correctIndex);
  }

  return (
    <div className={styles.card}>
      <p className={styles.question}>
        <strong>Q{questionNumber}.</strong> {question}
      </p>
      <div className={styles.options}>
        {options.map((opt, i) => {
          let cls = styles.option;
          if (submitted) {
            if (i === correctIndex) cls += ' ' + styles.correct;
            else if (i === selected) cls += ' ' + styles.wrong;
          } else if (i === selected) {
            cls += ' ' + styles.selected;
          }
          return (
            <label key={i} className={cls}>
              <input
                type="radio"
                name={`q-${questionNumber}`}
                checked={selected === i}
                onChange={() => !submitted && setSelected(i)}
                disabled={submitted}
              />
              {opt}
            </label>
          );
        })}
      </div>
      {!submitted && (
        <button className={styles.checkBtn} onClick={handleSubmit} disabled={selected === null}>
          Check Answer
        </button>
      )}
      {submitted && (
        <p className={selected === correctIndex ? styles.correctMsg : styles.wrongMsg}>
          {selected === correctIndex ? 'Correct!' : `Incorrect. The answer is: ${options[correctIndex]}`}
        </p>
      )}
    </div>
  );
}
