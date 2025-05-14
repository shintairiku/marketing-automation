// チャットメッセージの型定義
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

// 編集指示の型定義
export interface EditInstruction {
  id: string;
  type: 'replace' | 'add' | 'delete' | 'rewrite';
  targetSectionId?: string;
  targetText?: string;
  replacementText?: string;
  position?: 'before' | 'after' | 'within';
  instruction: string; // ユーザーの指示内容
}

// 編集履歴の型定義
export interface EditHistory {
  id: string;
  articleId: string;
  instructions: EditInstruction[];
  timestamp: string;
  appliedChanges: boolean;
}

// チャット会話履歴の型定義
export interface ChatSession {
  id: string;
  articleId: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

// APIレスポンスの型定義
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
