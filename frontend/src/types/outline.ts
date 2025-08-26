// アウトライン編集用の新しい型定義
export interface OutlineNode {
  id: string;          // 一意識別子
  title: string;       // 見出しテキスト
  level: number;       // 階層レベル (1..6, h1..h6相当)
  children: OutlineNode[];  // 子ノード
}

export interface OutlineTree {
  title?: string;            // 記事全体のタイトル（任意）
  description?: string;      // 記事の説明（任意）
  suggested_tone?: string;   // 推奨トーン（既存互換）
  nodes: OutlineNode[];      // ルート直下のセクション群
}

// 旧形式との互換性を保つための型定義
export interface LegacySection {
  title?: string;
  heading?: string;  // heading フィールドもサポート
  estimated_chars?: number;
  subsections?: LegacySection[];
}

export interface LegacyOutline {
  title?: string;
  description?: string;
  suggested_tone?: string;
  sections?: LegacySection[];
}

// Union型 - 新旧どちらも受け付ける
export type FlexibleOutline = OutlineTree | LegacyOutline;