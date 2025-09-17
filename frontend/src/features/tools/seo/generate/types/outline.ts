export type EditableOutlineSection = {
  heading: string;
  level: number;
  description?: string;
  estimated_chars?: number;
  subsections: EditableOutlineSection[];
};

export type EditableOutline = {
  title: string;
  suggested_tone?: string;
  topLevel: number;
  sections: EditableOutlineSection[];
};
