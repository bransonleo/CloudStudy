// POST /api/upload → 202
export interface UploadResponse {
  material_id: string;
  status: 'extracting';
}

// POST /api/generate/<material_id>
export type GenerationType = 'summary' | 'quiz' | 'flashcards';

export interface GenerateResponse {
  result_id: string;
  material_id: string;
  type: GenerationType;
  content: SummaryContent | QuizContent | FlashcardsContent;
  format_hint: string | null;
}

export interface SummaryContent {
  title: string;
  key_points: string[];
  summary: string;
}

export interface QuizContent {
  questions: QuizItem[];
}

export interface QuizItem {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface FlashcardsContent {
  flashcards: Flashcard[];
}

export interface Flashcard {
  front: string;
  back: string;
}

// GET /api/results/<material_id>
export interface BackendMaterial {
  material_id: string;
  filename: string;
  status: 'extracting' | 'ready' | 'error';
  error_message: string | null;
  results: {
    summary: ResultSlot<SummaryContent>;
    quiz: ResultSlot<QuizContent>;
    flashcards: ResultSlot<FlashcardsContent>;
  };
}

export interface ResultSlot<T> {
  status: 'done' | 'error' | 'not_requested';
  content?: T;
}

// API error shape (matches backend convention)
export interface ApiError {
  error: string;
  status: number;
}

// History entry stored in localStorage
export interface HistoryEntry {
  material_id: string;
  filename: string;
  timestamp: string;
  types: GenerationType[];
}
