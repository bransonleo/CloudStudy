// Upload response from POST /api/upload
export interface UploadResponse {
  material_id: string;
  filename: string;
  message: string;
}

// Request body for POST /api/generate
export interface GenerateRequest {
  material_id: string;
  types: GenerationType[];
}

export type GenerationType = 'summary' | 'quiz' | 'flashcards' | 'translation';

// Response from GET /api/results/<material_id>
export interface MaterialResult {
  material_id: string;
  filename: string;
  created_at: string;
  summary?: string;
  quiz?: QuizItem[];
  flashcards?: Flashcard[];
  translation?: string;
}

export interface QuizItem {
  question: string;
  options: string[];
  correct_index: number;
}

export interface Flashcard {
  front: string;
  back: string;
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
