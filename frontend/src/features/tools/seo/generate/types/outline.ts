// UI-safe types for editing only main sections of an outline
export type MainSection = {
  heading: string;
  estimated_chars?: number;
  // Keep existing subsections hidden in UI but preserved in payload
  __subsections?: string[];
};

export type EditableOutline = {
  title: string;
  suggested_tone?: string;
  sections: MainSection[];
};

