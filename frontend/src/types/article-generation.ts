// Article Generation Types
// This file contains type definitions extracted from the deprecated useArticleGeneration hook
// for use in the new Supabase Realtime implementation

export interface GenerationStep {
  id: string;
  name?: string; // For new implementation
  title?: string; // For legacy implementation  
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
  data?: any;
}

export interface PersonaOption {
  id: number;
  description: string;
}

export interface PersonaData extends PersonaOption {}

export interface ThemeOption {
  title: string;
  description: string;
  keywords: string[];
}

export interface ThemeData extends ThemeOption {}

export interface ResearchProgress {
  currentQuery: number;
  totalQueries: number;
  query: string;
}

export interface SectionsProgress {
  currentSection: number;
  totalSections: number;
  sectionHeading: string;
}

export interface ImagePlaceholder {
  placeholder_id: string;
  description_jp: string;
  prompt_en: string;
  alt_text: string;
}

export interface CompletedSection {
  index: number;
  heading: string;
  content: string;
  imagePlaceholders?: ImagePlaceholder[];
}

export interface GenerationState {
  currentStep: string;
  steps: GenerationStep[];
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  currentSection?: {
    index: number;
    heading: string;
    content: string;
  };
  finalArticle?: {
    title: string;
    content: string;
  };
  articleId?: string;
  isWaitingForInput: boolean;
  inputType?: string;
  error?: string;
  researchProgress?: ResearchProgress;
  sectionsProgress?: SectionsProgress;
  // Image mode related
  imageMode?: boolean;
  imagePlaceholders?: ImagePlaceholder[];
  // Section completion data for image mode
  completedSections?: CompletedSection[];
}

// Input types for user interactions
export type UserInputType = 
  | 'select_persona'
  | 'select_theme'
  | 'approve_plan'
  | 'approve_outline';

// Additional interfaces for new implementation
export interface ConnectionState {
  isInitializing: boolean;
  hasStarted: boolean;
}

export interface UseArticleGenerationOptions {
  processId?: string;
  userId?: string;
  autoConnect?: boolean;
}

// Step status types
export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error';

// API response types
export interface ProcessData {
  current_step?: string;
  is_waiting_for_input?: boolean;
  input_type?: string;
  [key: string]: any;
}