import { useState } from 'react';
import styles from './FlashCard.module.css';

interface Props {
  front: string;
  back: string;
  index: number;
  total: number;
  onNext: () => void;
  onPrev: () => void;
}

export default function FlashCard({
  front,
  back,
  index,
  total,
  onNext,
  onPrev,
}: Props) {
  const [flipped, setFlipped] = useState(false);

  function handleNext() {
    setFlipped(false);
    onNext();
  }

  function handlePrev() {
    setFlipped(false);
    onPrev();
  }

  return (
    <div className={styles.container}>
      <div className={styles.counter}>
        {index + 1} / {total}
      </div>

      <div className={styles.cardWrapper} onClick={() => setFlipped((f) => !f)}>
        <div className={`${styles.card} ${flipped ? styles.flipped : ''}`}>
          <div className={`${styles.face} ${styles.front}`}>
            <p className={styles.cardText}>{front}</p>
            <span className={styles.hint}>See answer</span>
          </div>
          <div className={`${styles.face} ${styles.back}`}>
            <p className={styles.cardText}>{back}</p>
            <span className={styles.hint}>See question</span>
          </div>
        </div>
      </div>

      <div className={styles.controls}>
        <button
          className={styles.navBtn}
          onClick={handlePrev}
          disabled={index === 0}
          aria-label="Previous card"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>

        <button
          className={styles.navBtn}
          onClick={handleNext}
          disabled={index === total - 1}
          aria-label="Next card"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>
      </div>
    </div>
  );
}
