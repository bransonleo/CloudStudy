import { useState } from 'react';
import styles from './FlashCard.module.css';

interface Props {
  front: string;
  back: string;
}

export default function FlashCard({ front, back }: Props) {
  const [flipped, setFlipped] = useState(false);

  return (
    <div className={styles.wrapper} onClick={() => setFlipped(!flipped)}>
      <div className={`${styles.inner} ${flipped ? styles.flipped : ''}`}>
        <div className={styles.face + ' ' + styles.front}>
          <p>{front}</p>
          <span className={styles.hint}>Click to flip</span>
        </div>
        <div className={styles.face + ' ' + styles.back}>
          <p>{back}</p>
          <span className={styles.hint}>Click to flip back</span>
        </div>
      </div>
    </div>
  );
}
