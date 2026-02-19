export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      agent_execution_logs: {
        Row: {
          agent_name: string
          agent_type: string
          cache_tokens: number | null
          completed_at: string | null
          duration_ms: number | null
          error_details: Json | null
          error_message: string | null
          execution_metadata: Json | null
          id: string
          input_data: Json | null
          input_tokens: number | null
          llm_model: string | null
          llm_provider: string | null
          output_data: Json | null
          output_tokens: number | null
          reasoning_tokens: number | null
          session_id: string
          started_at: string
          status: string
          step_number: number
          sub_step_number: number | null
        }
        Insert: {
          agent_name: string
          agent_type: string
          cache_tokens?: number | null
          completed_at?: string | null
          duration_ms?: number | null
          error_details?: Json | null
          error_message?: string | null
          execution_metadata?: Json | null
          id?: string
          input_data?: Json | null
          input_tokens?: number | null
          llm_model?: string | null
          llm_provider?: string | null
          output_data?: Json | null
          output_tokens?: number | null
          reasoning_tokens?: number | null
          session_id: string
          started_at?: string
          status?: string
          step_number: number
          sub_step_number?: number | null
        }
        Update: {
          agent_name?: string
          agent_type?: string
          cache_tokens?: number | null
          completed_at?: string | null
          duration_ms?: number | null
          error_details?: Json | null
          error_message?: string | null
          execution_metadata?: Json | null
          id?: string
          input_data?: Json | null
          input_tokens?: number | null
          llm_model?: string | null
          llm_provider?: string | null
          output_data?: Json | null
          output_tokens?: number | null
          reasoning_tokens?: number | null
          session_id?: string
          started_at?: string
          status?: string
          step_number?: number
          sub_step_number?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "agent_execution_logs_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "agent_log_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_log_sessions: {
        Row: {
          article_style_info: Json | null
          article_uuid: string
          company_info: Json | null
          completed_at: string | null
          completed_steps: number | null
          created_at: string
          generation_theme_count: number | null
          id: string
          image_mode_enabled: boolean | null
          initial_input: Json
          organization_id: string | null
          persona_settings: Json | null
          seo_keywords: string[] | null
          session_metadata: Json | null
          status: string
          target_age_group: string | null
          total_steps: number | null
          updated_at: string
          user_id: string
        }
        Insert: {
          article_style_info?: Json | null
          article_uuid: string
          company_info?: Json | null
          completed_at?: string | null
          completed_steps?: number | null
          created_at?: string
          generation_theme_count?: number | null
          id?: string
          image_mode_enabled?: boolean | null
          initial_input?: Json
          organization_id?: string | null
          persona_settings?: Json | null
          seo_keywords?: string[] | null
          session_metadata?: Json | null
          status?: string
          target_age_group?: string | null
          total_steps?: number | null
          updated_at?: string
          user_id: string
        }
        Update: {
          article_style_info?: Json | null
          article_uuid?: string
          company_info?: Json | null
          completed_at?: string | null
          completed_steps?: number | null
          created_at?: string
          generation_theme_count?: number | null
          id?: string
          image_mode_enabled?: boolean | null
          initial_input?: Json
          organization_id?: string | null
          persona_settings?: Json | null
          seo_keywords?: string[] | null
          session_metadata?: Json | null
          status?: string
          target_age_group?: string | null
          total_steps?: number | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      article_agent_messages: {
        Row: {
          content: string | null
          created_at: string
          id: string
          metadata: Json | null
          role: string
          sequence: number
          session_id: string
          user_id: string
        }
        Insert: {
          content?: string | null
          created_at?: string
          id?: string
          metadata?: Json | null
          role: string
          sequence?: never
          session_id: string
          user_id: string
        }
        Update: {
          content?: string | null
          created_at?: string
          id?: string
          metadata?: Json | null
          role?: string
          sequence?: never
          session_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "article_agent_messages_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "article_agent_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      article_agent_sessions: {
        Row: {
          article_id: string
          article_title: string | null
          closed_at: string | null
          conversation_summary: string | null
          created_at: string
          id: string
          last_activity_at: string
          metadata: Json | null
          organization_id: string | null
          original_content: string | null
          session_store_key: string
          status: string
          updated_at: string
          user_id: string
          working_content: string | null
        }
        Insert: {
          article_id: string
          article_title?: string | null
          closed_at?: string | null
          conversation_summary?: string | null
          created_at?: string
          id?: string
          last_activity_at?: string
          metadata?: Json | null
          organization_id?: string | null
          original_content?: string | null
          session_store_key: string
          status?: string
          updated_at?: string
          user_id: string
          working_content?: string | null
        }
        Update: {
          article_id?: string
          article_title?: string | null
          closed_at?: string | null
          conversation_summary?: string | null
          created_at?: string
          id?: string
          last_activity_at?: string
          metadata?: Json | null
          organization_id?: string | null
          original_content?: string | null
          session_store_key?: string
          status?: string
          updated_at?: string
          user_id?: string
          working_content?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "article_agent_sessions_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "article_agent_sessions_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      article_edit_versions: {
        Row: {
          article_id: string
          change_description: string | null
          content: string
          created_at: string | null
          id: string
          is_current: boolean | null
          metadata: Json | null
          title: string | null
          user_id: string
          version_number: number
        }
        Insert: {
          article_id: string
          change_description?: string | null
          content: string
          created_at?: string | null
          id?: string
          is_current?: boolean | null
          metadata?: Json | null
          title?: string | null
          user_id: string
          version_number: number
        }
        Update: {
          article_id?: string
          change_description?: string | null
          content?: string
          created_at?: string | null
          id?: string
          is_current?: boolean | null
          metadata?: Json | null
          title?: string | null
          user_id?: string
          version_number?: number
        }
        Relationships: [
          {
            foreignKeyName: "article_edit_versions_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
        ]
      }
      article_generation_flows: {
        Row: {
          created_at: string
          description: string | null
          id: string
          is_template: boolean | null
          name: string
          organization_id: string | null
          updated_at: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          description?: string | null
          id?: string
          is_template?: boolean | null
          name: string
          organization_id?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          description?: string | null
          id?: string
          is_template?: boolean | null
          name?: string
          organization_id?: string | null
          updated_at?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "article_generation_flows_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      article_generation_step_snapshots: {
        Row: {
          article_context: Json
          branch_id: string | null
          branch_name: string | null
          can_restore: boolean | null
          created_at: string | null
          id: string
          is_active_branch: boolean | null
          parent_snapshot_id: string | null
          process_id: string
          process_metadata: Json | null
          snapshot_metadata: Json | null
          step_category: string | null
          step_description: string | null
          step_index: number
          step_name: string
        }
        Insert: {
          article_context?: Json
          branch_id?: string | null
          branch_name?: string | null
          can_restore?: boolean | null
          created_at?: string | null
          id?: string
          is_active_branch?: boolean | null
          parent_snapshot_id?: string | null
          process_id: string
          process_metadata?: Json | null
          snapshot_metadata?: Json | null
          step_category?: string | null
          step_description?: string | null
          step_index?: number
          step_name: string
        }
        Update: {
          article_context?: Json
          branch_id?: string | null
          branch_name?: string | null
          can_restore?: boolean | null
          created_at?: string | null
          id?: string
          is_active_branch?: boolean | null
          parent_snapshot_id?: string | null
          process_id?: string
          process_metadata?: Json | null
          snapshot_metadata?: Json | null
          step_category?: string | null
          step_description?: string | null
          step_index?: number
          step_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "article_generation_step_snapshots_parent_snapshot_id_fkey"
            columns: ["parent_snapshot_id"]
            isOneToOne: false
            referencedRelation: "article_generation_step_snapshots"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "article_generation_step_snapshots_process_id_fkey"
            columns: ["process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
        ]
      }
      articles: {
        Row: {
          content: string
          created_at: string
          generation_process_id: string | null
          id: string
          keywords: string[] | null
          organization_id: string | null
          status: string | null
          target_audience: string | null
          title: string
          updated_at: string
          user_id: string
        }
        Insert: {
          content: string
          created_at?: string
          generation_process_id?: string | null
          id?: string
          keywords?: string[] | null
          organization_id?: string | null
          status?: string | null
          target_audience?: string | null
          title: string
          updated_at?: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string
          generation_process_id?: string | null
          id?: string
          keywords?: string[] | null
          organization_id?: string | null
          status?: string | null
          target_audience?: string | null
          title?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "articles_generation_process_id_fkey"
            columns: ["generation_process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "articles_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      background_tasks: {
        Row: {
          blocks_tasks: string[] | null
          completed_at: string | null
          created_at: string | null
          created_by: string | null
          depends_on: string[] | null
          error_details: Json | null
          error_message: string | null
          estimated_duration: unknown
          execution_time: unknown
          heartbeat_at: string | null
          id: string
          max_retries: number | null
          priority: number | null
          process_id: string
          resource_usage: Json | null
          retry_count: number | null
          retry_delay_seconds: number | null
          scheduled_for: string | null
          started_at: string | null
          status: string | null
          tags: string[] | null
          task_data: Json
          task_type: string
          updated_at: string | null
          worker_hostname: string | null
          worker_id: string | null
        }
        Insert: {
          blocks_tasks?: string[] | null
          completed_at?: string | null
          created_at?: string | null
          created_by?: string | null
          depends_on?: string[] | null
          error_details?: Json | null
          error_message?: string | null
          estimated_duration?: unknown
          execution_time?: unknown
          heartbeat_at?: string | null
          id?: string
          max_retries?: number | null
          priority?: number | null
          process_id: string
          resource_usage?: Json | null
          retry_count?: number | null
          retry_delay_seconds?: number | null
          scheduled_for?: string | null
          started_at?: string | null
          status?: string | null
          tags?: string[] | null
          task_data?: Json
          task_type: string
          updated_at?: string | null
          worker_hostname?: string | null
          worker_id?: string | null
        }
        Update: {
          blocks_tasks?: string[] | null
          completed_at?: string | null
          created_at?: string | null
          created_by?: string | null
          depends_on?: string[] | null
          error_details?: Json | null
          error_message?: string | null
          estimated_duration?: unknown
          execution_time?: unknown
          heartbeat_at?: string | null
          id?: string
          max_retries?: number | null
          priority?: number | null
          process_id?: string
          resource_usage?: Json | null
          retry_count?: number | null
          retry_delay_seconds?: number | null
          scheduled_for?: string | null
          started_at?: string | null
          status?: string | null
          tags?: string[] | null
          task_data?: Json
          task_type?: string
          updated_at?: string | null
          worker_hostname?: string | null
          worker_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "background_tasks_process_id_fkey"
            columns: ["process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
        ]
      }
      blog_generation_state: {
        Row: {
          blog_context: Json | null
          created_at: string | null
          current_step_name: string | null
          draft_edit_url: string | null
          draft_post_id: number | null
          draft_preview_url: string | null
          error_message: string | null
          id: string
          input_type: string | null
          is_waiting_for_input: boolean | null
          last_realtime_event: Json | null
          organization_id: string | null
          progress_percentage: number | null
          realtime_channel: string | null
          reference_url: string | null
          response_id: string | null
          status: string | null
          updated_at: string | null
          uploaded_images: Json | null
          user_id: string
          user_prompt: string | null
          wordpress_site_id: string | null
        }
        Insert: {
          blog_context?: Json | null
          created_at?: string | null
          current_step_name?: string | null
          draft_edit_url?: string | null
          draft_post_id?: number | null
          draft_preview_url?: string | null
          error_message?: string | null
          id?: string
          input_type?: string | null
          is_waiting_for_input?: boolean | null
          last_realtime_event?: Json | null
          organization_id?: string | null
          progress_percentage?: number | null
          realtime_channel?: string | null
          reference_url?: string | null
          response_id?: string | null
          status?: string | null
          updated_at?: string | null
          uploaded_images?: Json | null
          user_id: string
          user_prompt?: string | null
          wordpress_site_id?: string | null
        }
        Update: {
          blog_context?: Json | null
          created_at?: string | null
          current_step_name?: string | null
          draft_edit_url?: string | null
          draft_post_id?: number | null
          draft_preview_url?: string | null
          error_message?: string | null
          id?: string
          input_type?: string | null
          is_waiting_for_input?: boolean | null
          last_realtime_event?: Json | null
          organization_id?: string | null
          progress_percentage?: number | null
          realtime_channel?: string | null
          reference_url?: string | null
          response_id?: string | null
          status?: string | null
          updated_at?: string | null
          uploaded_images?: Json | null
          user_id?: string
          user_prompt?: string | null
          wordpress_site_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "blog_generation_state_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "blog_generation_state_wordpress_site_id_fkey"
            columns: ["wordpress_site_id"]
            isOneToOne: false
            referencedRelation: "wordpress_sites"
            referencedColumns: ["id"]
          },
        ]
      }
      blog_process_events: {
        Row: {
          created_at: string | null
          event_data: Json | null
          event_sequence: number
          event_type: string
          id: string
          process_id: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          event_data?: Json | null
          event_sequence?: number
          event_type: string
          id?: string
          process_id: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          event_data?: Json | null
          event_sequence?: number
          event_type?: string
          id?: string
          process_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "blog_process_events_process_id_fkey"
            columns: ["process_id"]
            isOneToOne: false
            referencedRelation: "blog_generation_state"
            referencedColumns: ["id"]
          },
        ]
      }
      company_info: {
        Row: {
          avoid_terms: string | null
          brand_slogan: string | null
          created_at: string
          description: string
          id: string
          industry_terms: string | null
          is_default: boolean
          name: string
          popular_articles: string | null
          target_area: string | null
          target_keywords: string | null
          target_persona: string
          updated_at: string
          user_id: string
          usp: string
          website_url: string
        }
        Insert: {
          avoid_terms?: string | null
          brand_slogan?: string | null
          created_at?: string
          description: string
          id?: string
          industry_terms?: string | null
          is_default?: boolean
          name: string
          popular_articles?: string | null
          target_area?: string | null
          target_keywords?: string | null
          target_persona: string
          updated_at?: string
          user_id: string
          usp: string
          website_url: string
        }
        Update: {
          avoid_terms?: string | null
          brand_slogan?: string | null
          created_at?: string
          description?: string
          id?: string
          industry_terms?: string | null
          is_default?: boolean
          name?: string
          popular_articles?: string | null
          target_area?: string | null
          target_keywords?: string | null
          target_persona?: string
          updated_at?: string
          user_id?: string
          usp?: string
          website_url?: string
        }
        Relationships: []
      }
      flow_steps: {
        Row: {
          agent_name: string | null
          config: Json | null
          flow_id: string
          id: string
          is_interactive: boolean | null
          output_schema: Json | null
          prompt_template_id: string | null
          skippable: boolean | null
          step_order: number
          step_type: Database["public"]["Enums"]["step_type"]
          tool_config: Json | null
        }
        Insert: {
          agent_name?: string | null
          config?: Json | null
          flow_id: string
          id?: string
          is_interactive?: boolean | null
          output_schema?: Json | null
          prompt_template_id?: string | null
          skippable?: boolean | null
          step_order: number
          step_type: Database["public"]["Enums"]["step_type"]
          tool_config?: Json | null
        }
        Update: {
          agent_name?: string | null
          config?: Json | null
          flow_id?: string
          id?: string
          is_interactive?: boolean | null
          output_schema?: Json | null
          prompt_template_id?: string | null
          skippable?: boolean | null
          step_order?: number
          step_type?: Database["public"]["Enums"]["step_type"]
          tool_config?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "flow_steps_flow_id_fkey"
            columns: ["flow_id"]
            isOneToOne: false
            referencedRelation: "article_generation_flows"
            referencedColumns: ["id"]
          },
        ]
      }
      generated_articles_state: {
        Row: {
          article_context: Json
          article_id: string | null
          auto_resume_eligible: boolean | null
          background_task_id: string | null
          created_at: string
          current_snapshot_id: string | null
          current_step_id: string | null
          current_step_name: string | null
          error_message: string | null
          estimated_completion_time: string | null
          executing_step: string | null
          flow_id: string | null
          generated_content: Json | null
          id: string
          image_mode: boolean | null
          image_settings: Json | null
          input_reminder_sent: boolean | null
          input_type: string | null
          interaction_history: Json | null
          is_waiting_for_input: boolean | null
          last_activity_at: string | null
          last_realtime_event: Json | null
          max_retries: number | null
          organization_id: string | null
          parent_process_id: string | null
          process_metadata: Json | null
          process_tags: string[] | null
          process_type: string | null
          progress_percentage: number | null
          realtime_channel: string | null
          realtime_subscriptions: Json | null
          resume_from_step: string | null
          retry_count: number | null
          status: Database["public"]["Enums"]["generation_status"]
          step_durations: Json | null
          step_execution_metadata: Json | null
          step_execution_start: string | null
          step_history: Json | null
          style_template_id: string | null
          task_priority: number | null
          total_processing_time: unknown
          updated_at: string
          user_id: string
          user_input_timeout: string | null
        }
        Insert: {
          article_context: Json
          article_id?: string | null
          auto_resume_eligible?: boolean | null
          background_task_id?: string | null
          created_at?: string
          current_snapshot_id?: string | null
          current_step_id?: string | null
          current_step_name?: string | null
          error_message?: string | null
          estimated_completion_time?: string | null
          executing_step?: string | null
          flow_id?: string | null
          generated_content?: Json | null
          id?: string
          image_mode?: boolean | null
          image_settings?: Json | null
          input_reminder_sent?: boolean | null
          input_type?: string | null
          interaction_history?: Json | null
          is_waiting_for_input?: boolean | null
          last_activity_at?: string | null
          last_realtime_event?: Json | null
          max_retries?: number | null
          organization_id?: string | null
          parent_process_id?: string | null
          process_metadata?: Json | null
          process_tags?: string[] | null
          process_type?: string | null
          progress_percentage?: number | null
          realtime_channel?: string | null
          realtime_subscriptions?: Json | null
          resume_from_step?: string | null
          retry_count?: number | null
          status?: Database["public"]["Enums"]["generation_status"]
          step_durations?: Json | null
          step_execution_metadata?: Json | null
          step_execution_start?: string | null
          step_history?: Json | null
          style_template_id?: string | null
          task_priority?: number | null
          total_processing_time?: unknown
          updated_at?: string
          user_id: string
          user_input_timeout?: string | null
        }
        Update: {
          article_context?: Json
          article_id?: string | null
          auto_resume_eligible?: boolean | null
          background_task_id?: string | null
          created_at?: string
          current_snapshot_id?: string | null
          current_step_id?: string | null
          current_step_name?: string | null
          error_message?: string | null
          estimated_completion_time?: string | null
          executing_step?: string | null
          flow_id?: string | null
          generated_content?: Json | null
          id?: string
          image_mode?: boolean | null
          image_settings?: Json | null
          input_reminder_sent?: boolean | null
          input_type?: string | null
          interaction_history?: Json | null
          is_waiting_for_input?: boolean | null
          last_activity_at?: string | null
          last_realtime_event?: Json | null
          max_retries?: number | null
          organization_id?: string | null
          parent_process_id?: string | null
          process_metadata?: Json | null
          process_tags?: string[] | null
          process_type?: string | null
          progress_percentage?: number | null
          realtime_channel?: string | null
          realtime_subscriptions?: Json | null
          resume_from_step?: string | null
          retry_count?: number | null
          status?: Database["public"]["Enums"]["generation_status"]
          step_durations?: Json | null
          step_execution_metadata?: Json | null
          step_execution_start?: string | null
          step_history?: Json | null
          style_template_id?: string | null
          task_priority?: number | null
          total_processing_time?: unknown
          updated_at?: string
          user_id?: string
          user_input_timeout?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "generated_articles_state_current_snapshot_id_fkey"
            columns: ["current_snapshot_id"]
            isOneToOne: false
            referencedRelation: "article_generation_step_snapshots"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_state_current_step_id_fkey"
            columns: ["current_step_id"]
            isOneToOne: false
            referencedRelation: "flow_steps"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_state_flow_id_fkey"
            columns: ["flow_id"]
            isOneToOne: false
            referencedRelation: "article_generation_flows"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_state_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_state_parent_process_id_fkey"
            columns: ["parent_process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_state_style_template_id_fkey"
            columns: ["style_template_id"]
            isOneToOne: false
            referencedRelation: "style_guide_templates"
            referencedColumns: ["id"]
          },
        ]
      }
      image_placeholders: {
        Row: {
          article_id: string | null
          created_at: string
          description_jp: string
          generation_process_id: string | null
          id: string
          metadata: Json | null
          placeholder_id: string
          position_index: number
          prompt_en: string
          replaced_with_image_id: string | null
          status: string | null
          updated_at: string
        }
        Insert: {
          article_id?: string | null
          created_at?: string
          description_jp: string
          generation_process_id?: string | null
          id?: string
          metadata?: Json | null
          placeholder_id: string
          position_index: number
          prompt_en: string
          replaced_with_image_id?: string | null
          status?: string | null
          updated_at?: string
        }
        Update: {
          article_id?: string | null
          created_at?: string
          description_jp?: string
          generation_process_id?: string | null
          id?: string
          metadata?: Json | null
          placeholder_id?: string
          position_index?: number
          prompt_en?: string
          replaced_with_image_id?: string | null
          status?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "image_placeholders_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "image_placeholders_generation_process_id_fkey"
            columns: ["generation_process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "image_placeholders_replaced_with_image_id_fkey"
            columns: ["replaced_with_image_id"]
            isOneToOne: false
            referencedRelation: "images"
            referencedColumns: ["id"]
          },
        ]
      }
      images: {
        Row: {
          alt_text: string | null
          article_id: string | null
          caption: string | null
          created_at: string
          file_path: string
          gcs_path: string | null
          gcs_url: string | null
          generation_params: Json | null
          generation_process_id: string | null
          generation_prompt: string | null
          id: string
          image_type: string
          metadata: Json | null
          organization_id: string | null
          original_filename: string | null
          storage_type: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          alt_text?: string | null
          article_id?: string | null
          caption?: string | null
          created_at?: string
          file_path: string
          gcs_path?: string | null
          gcs_url?: string | null
          generation_params?: Json | null
          generation_process_id?: string | null
          generation_prompt?: string | null
          id?: string
          image_type: string
          metadata?: Json | null
          organization_id?: string | null
          original_filename?: string | null
          storage_type?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          alt_text?: string | null
          article_id?: string | null
          caption?: string | null
          created_at?: string
          file_path?: string
          gcs_path?: string | null
          gcs_url?: string | null
          generation_params?: Json | null
          generation_process_id?: string | null
          generation_prompt?: string | null
          id?: string
          image_type?: string
          metadata?: Json | null
          organization_id?: string | null
          original_filename?: string | null
          storage_type?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "images_article_id_fkey"
            columns: ["article_id"]
            isOneToOne: false
            referencedRelation: "articles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "images_generation_process_id_fkey"
            columns: ["generation_process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "images_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      invitations: {
        Row: {
          created_at: string
          email: string
          expires_at: string
          id: string
          invited_by_user_id: string
          organization_id: string
          role: Database["public"]["Enums"]["organization_role"]
          status: Database["public"]["Enums"]["invitation_status"]
          token: string
        }
        Insert: {
          created_at?: string
          email: string
          expires_at?: string
          id?: string
          invited_by_user_id: string
          organization_id: string
          role?: Database["public"]["Enums"]["organization_role"]
          status?: Database["public"]["Enums"]["invitation_status"]
          token?: string
        }
        Update: {
          created_at?: string
          email?: string
          expires_at?: string
          id?: string
          invited_by_user_id?: string
          organization_id?: string
          role?: Database["public"]["Enums"]["organization_role"]
          status?: Database["public"]["Enums"]["invitation_status"]
          token?: string
        }
        Relationships: [
          {
            foreignKeyName: "invitations_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      llm_call_logs: {
        Row: {
          api_response_id: string | null
          api_type: string
          cached_tokens: number | null
          call_sequence: number
          called_at: string
          completion_tokens: number | null
          error_message: string | null
          error_type: string | null
          estimated_cost_usd: number | null
          execution_id: string
          full_prompt_data: Json | null
          http_status_code: number | null
          id: string
          model_name: string
          prompt_tokens: number | null
          provider: string
          reasoning_tokens: number | null
          response_content: string | null
          response_data: Json | null
          response_time_ms: number | null
          retry_count: number | null
          system_prompt: string | null
          total_tokens: number | null
          user_prompt: string | null
        }
        Insert: {
          api_response_id?: string | null
          api_type?: string
          cached_tokens?: number | null
          call_sequence?: number
          called_at?: string
          completion_tokens?: number | null
          error_message?: string | null
          error_type?: string | null
          estimated_cost_usd?: number | null
          execution_id: string
          full_prompt_data?: Json | null
          http_status_code?: number | null
          id?: string
          model_name: string
          prompt_tokens?: number | null
          provider?: string
          reasoning_tokens?: number | null
          response_content?: string | null
          response_data?: Json | null
          response_time_ms?: number | null
          retry_count?: number | null
          system_prompt?: string | null
          total_tokens?: number | null
          user_prompt?: string | null
        }
        Update: {
          api_response_id?: string | null
          api_type?: string
          cached_tokens?: number | null
          call_sequence?: number
          called_at?: string
          completion_tokens?: number | null
          error_message?: string | null
          error_type?: string | null
          estimated_cost_usd?: number | null
          execution_id?: string
          full_prompt_data?: Json | null
          http_status_code?: number | null
          id?: string
          model_name?: string
          prompt_tokens?: number | null
          provider?: string
          reasoning_tokens?: number | null
          response_content?: string | null
          response_data?: Json | null
          response_time_ms?: number | null
          retry_count?: number | null
          system_prompt?: string | null
          total_tokens?: number | null
          user_prompt?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "llm_call_logs_execution_id_fkey"
            columns: ["execution_id"]
            isOneToOne: false
            referencedRelation: "agent_execution_logs"
            referencedColumns: ["id"]
          },
        ]
      }
      organization_members: {
        Row: {
          clerk_membership_id: string | null
          display_name: string | null
          email: string | null
          joined_at: string
          organization_id: string
          role: Database["public"]["Enums"]["organization_role"]
          user_id: string
        }
        Insert: {
          clerk_membership_id?: string | null
          display_name?: string | null
          email?: string | null
          joined_at?: string
          organization_id: string
          role?: Database["public"]["Enums"]["organization_role"]
          user_id: string
        }
        Update: {
          clerk_membership_id?: string | null
          display_name?: string | null
          email?: string | null
          joined_at?: string
          organization_id?: string
          role?: Database["public"]["Enums"]["organization_role"]
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "organization_members_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      organization_subscriptions: {
        Row: {
          addon_quantity: number
          cancel_at: string | null
          cancel_at_period_end: boolean | null
          canceled_at: string | null
          created: string
          current_period_end: string
          current_period_start: string
          ended_at: string | null
          id: string
          metadata: Json | null
          organization_id: string
          plan_tier_id: string | null
          price_id: string | null
          quantity: number
          status: Database["public"]["Enums"]["subscription_status"]
          trial_end: string | null
          trial_start: string | null
        }
        Insert: {
          addon_quantity?: number
          cancel_at?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          created?: string
          current_period_end?: string
          current_period_start?: string
          ended_at?: string | null
          id: string
          metadata?: Json | null
          organization_id: string
          plan_tier_id?: string | null
          price_id?: string | null
          quantity?: number
          status: Database["public"]["Enums"]["subscription_status"]
          trial_end?: string | null
          trial_start?: string | null
        }
        Update: {
          addon_quantity?: number
          cancel_at?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          created?: string
          current_period_end?: string
          current_period_start?: string
          ended_at?: string | null
          id?: string
          metadata?: Json | null
          organization_id?: string
          plan_tier_id?: string | null
          price_id?: string | null
          quantity?: number
          status?: Database["public"]["Enums"]["subscription_status"]
          trial_end?: string | null
          trial_start?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "organization_subscriptions_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "organization_subscriptions_plan_tier_id_fkey"
            columns: ["plan_tier_id"]
            isOneToOne: false
            referencedRelation: "plan_tiers"
            referencedColumns: ["id"]
          },
        ]
      }
      organizations: {
        Row: {
          billing_user_id: string | null
          clerk_organization_id: string | null
          created_at: string
          id: string
          name: string
          owner_user_id: string
          stripe_customer_id: string | null
          updated_at: string
        }
        Insert: {
          billing_user_id?: string | null
          clerk_organization_id?: string | null
          created_at?: string
          id?: string
          name: string
          owner_user_id: string
          stripe_customer_id?: string | null
          updated_at?: string
        }
        Update: {
          billing_user_id?: string | null
          clerk_organization_id?: string | null
          created_at?: string
          id?: string
          name?: string
          owner_user_id?: string
          stripe_customer_id?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      plan_tiers: {
        Row: {
          addon_unit_amount: number
          created_at: string | null
          display_order: number
          id: string
          is_active: boolean
          monthly_article_limit: number
          name: string
          price_amount: number
          stripe_price_id: string
          updated_at: string | null
        }
        Insert: {
          addon_unit_amount?: number
          created_at?: string | null
          display_order?: number
          id: string
          is_active?: boolean
          monthly_article_limit: number
          name: string
          price_amount: number
          stripe_price_id: string
          updated_at?: string | null
        }
        Update: {
          addon_unit_amount?: number
          created_at?: string | null
          display_order?: number
          id?: string
          is_active?: boolean
          monthly_article_limit?: number
          name?: string
          price_amount?: number
          stripe_price_id?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      process_events: {
        Row: {
          acknowledged_by: string[] | null
          archived: boolean | null
          created_at: string | null
          delivery_attempts: number | null
          event_category: string | null
          event_data: Json
          event_priority: number | null
          event_sequence: number
          event_source: string | null
          event_type: string
          expires_at: string | null
          id: string
          process_id: string
          published_at: string | null
        }
        Insert: {
          acknowledged_by?: string[] | null
          archived?: boolean | null
          created_at?: string | null
          delivery_attempts?: number | null
          event_category?: string | null
          event_data?: Json
          event_priority?: number | null
          event_sequence: number
          event_source?: string | null
          event_type: string
          expires_at?: string | null
          id?: string
          process_id: string
          published_at?: string | null
        }
        Update: {
          acknowledged_by?: string[] | null
          archived?: boolean | null
          created_at?: string | null
          delivery_attempts?: number | null
          event_category?: string | null
          event_data?: Json
          event_priority?: number | null
          event_sequence?: number
          event_source?: string | null
          event_type?: string
          expires_at?: string | null
          id?: string
          process_id?: string
          published_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "process_events_process_id_fkey"
            columns: ["process_id"]
            isOneToOne: false
            referencedRelation: "generated_articles_state"
            referencedColumns: ["id"]
          },
        ]
      }
      style_guide_templates: {
        Row: {
          created_at: string
          description: string | null
          id: string
          is_active: boolean | null
          is_default: boolean | null
          name: string
          organization_id: string | null
          settings: Json
          template_type:
            | Database["public"]["Enums"]["style_template_type"]
            | null
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_default?: boolean | null
          name: string
          organization_id?: string | null
          settings?: Json
          template_type?:
            | Database["public"]["Enums"]["style_template_type"]
            | null
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_default?: boolean | null
          name?: string
          organization_id?: string | null
          settings?: Json
          template_type?:
            | Database["public"]["Enums"]["style_template_type"]
            | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "style_guide_templates_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      subscription_events: {
        Row: {
          created_at: string | null
          event_data: Json | null
          event_type: string
          id: string
          stripe_event_id: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          event_data?: Json | null
          event_type: string
          id?: string
          stripe_event_id?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          event_data?: Json | null
          event_type?: string
          id?: string
          stripe_event_id?: string | null
          user_id?: string
        }
        Relationships: []
      }
      tool_call_logs: {
        Row: {
          api_calls_count: number | null
          call_sequence: number
          called_at: string
          completed_at: string | null
          data_size_bytes: number | null
          error_message: string | null
          error_type: string | null
          execution_id: string
          execution_time_ms: number | null
          id: string
          input_parameters: Json | null
          output_data: Json | null
          retry_count: number | null
          status: string
          tool_function: string
          tool_metadata: Json | null
          tool_name: string
        }
        Insert: {
          api_calls_count?: number | null
          call_sequence?: number
          called_at?: string
          completed_at?: string | null
          data_size_bytes?: number | null
          error_message?: string | null
          error_type?: string | null
          execution_id: string
          execution_time_ms?: number | null
          id?: string
          input_parameters?: Json | null
          output_data?: Json | null
          retry_count?: number | null
          status?: string
          tool_function: string
          tool_metadata?: Json | null
          tool_name: string
        }
        Update: {
          api_calls_count?: number | null
          call_sequence?: number
          called_at?: string
          completed_at?: string | null
          data_size_bytes?: number | null
          error_message?: string | null
          error_type?: string | null
          execution_id?: string
          execution_time_ms?: number | null
          id?: string
          input_parameters?: Json | null
          output_data?: Json | null
          retry_count?: number | null
          status?: string
          tool_function?: string
          tool_metadata?: Json | null
          tool_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "tool_call_logs_execution_id_fkey"
            columns: ["execution_id"]
            isOneToOne: false
            referencedRelation: "agent_execution_logs"
            referencedColumns: ["id"]
          },
        ]
      }
      usage_logs: {
        Row: {
          created_at: string | null
          generation_process_id: string
          id: string
          usage_tracking_id: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          generation_process_id: string
          id?: string
          usage_tracking_id: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          generation_process_id?: string
          id?: string
          usage_tracking_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "usage_logs_usage_tracking_id_fkey"
            columns: ["usage_tracking_id"]
            isOneToOne: false
            referencedRelation: "usage_tracking"
            referencedColumns: ["id"]
          },
        ]
      }
      usage_tracking: {
        Row: {
          addon_articles_limit: number
          articles_generated: number
          articles_limit: number
          billing_period_end: string
          billing_period_start: string
          created_at: string | null
          id: string
          organization_id: string | null
          plan_tier_id: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          addon_articles_limit?: number
          articles_generated?: number
          articles_limit: number
          billing_period_end: string
          billing_period_start: string
          created_at?: string | null
          id?: string
          organization_id?: string | null
          plan_tier_id?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          addon_articles_limit?: number
          articles_generated?: number
          articles_limit?: number
          billing_period_end?: string
          billing_period_start?: string
          created_at?: string | null
          id?: string
          organization_id?: string | null
          plan_tier_id?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "usage_tracking_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "usage_tracking_plan_tier_id_fkey"
            columns: ["plan_tier_id"]
            isOneToOne: false
            referencedRelation: "plan_tiers"
            referencedColumns: ["id"]
          },
        ]
      }
      user_subscriptions: {
        Row: {
          addon_quantity: number
          cancel_at_period_end: boolean | null
          created_at: string | null
          current_period_end: string | null
          email: string | null
          is_privileged: boolean | null
          plan_tier_id: string | null
          status: Database["public"]["Enums"]["user_subscription_status"]
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          updated_at: string | null
          upgraded_to_org_id: string | null
          user_id: string
        }
        Insert: {
          addon_quantity?: number
          cancel_at_period_end?: boolean | null
          created_at?: string | null
          current_period_end?: string | null
          email?: string | null
          is_privileged?: boolean | null
          plan_tier_id?: string | null
          status?: Database["public"]["Enums"]["user_subscription_status"]
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          updated_at?: string | null
          upgraded_to_org_id?: string | null
          user_id: string
        }
        Update: {
          addon_quantity?: number
          cancel_at_period_end?: boolean | null
          created_at?: string | null
          current_period_end?: string | null
          email?: string | null
          is_privileged?: boolean | null
          plan_tier_id?: string | null
          status?: Database["public"]["Enums"]["user_subscription_status"]
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          updated_at?: string | null
          upgraded_to_org_id?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_subscriptions_plan_tier_id_fkey"
            columns: ["plan_tier_id"]
            isOneToOne: false
            referencedRelation: "plan_tiers"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_subscriptions_upgraded_to_org_id_fkey"
            columns: ["upgraded_to_org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      wordpress_sites: {
        Row: {
          connection_status: string | null
          created_at: string | null
          encrypted_credentials: string
          id: string
          is_active: boolean | null
          last_connected_at: string | null
          last_error: string | null
          last_used_at: string | null
          mcp_endpoint: string
          organization_id: string | null
          site_name: string | null
          site_url: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          connection_status?: string | null
          created_at?: string | null
          encrypted_credentials: string
          id?: string
          is_active?: boolean | null
          last_connected_at?: string | null
          last_error?: string | null
          last_used_at?: string | null
          mcp_endpoint: string
          organization_id?: string | null
          site_name?: string | null
          site_url: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          connection_status?: string | null
          created_at?: string | null
          encrypted_credentials?: string
          id?: string
          is_active?: boolean | null
          last_connected_at?: string | null
          last_error?: string | null
          last_used_at?: string | null
          mcp_endpoint?: string
          organization_id?: string | null
          site_name?: string | null
          site_url?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "wordpress_sites_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      workflow_step_logs: {
        Row: {
          completed_at: string | null
          duration_ms: number | null
          id: string
          intermediate_results: Json | null
          primary_execution_id: string | null
          session_id: string
          started_at: string | null
          status: string
          step_input: Json | null
          step_metadata: Json | null
          step_name: string
          step_order: number
          step_output: Json | null
          step_type: string
        }
        Insert: {
          completed_at?: string | null
          duration_ms?: number | null
          id?: string
          intermediate_results?: Json | null
          primary_execution_id?: string | null
          session_id: string
          started_at?: string | null
          status?: string
          step_input?: Json | null
          step_metadata?: Json | null
          step_name: string
          step_order: number
          step_output?: Json | null
          step_type: string
        }
        Update: {
          completed_at?: string | null
          duration_ms?: number | null
          id?: string
          intermediate_results?: Json | null
          primary_execution_id?: string | null
          session_id?: string
          started_at?: string | null
          status?: string
          step_input?: Json | null
          step_metadata?: Json | null
          step_name?: string
          step_order?: number
          step_output?: Json | null
          step_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "workflow_step_logs_primary_execution_id_fkey"
            columns: ["primary_execution_id"]
            isOneToOne: false
            referencedRelation: "agent_execution_logs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "workflow_step_logs_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "agent_log_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      add_step_to_history: {
        Args: {
          process_id: string
          step_data?: Json
          step_name: string
          step_status: string
        }
        Returns: undefined
      }
      cleanup_old_events: { Args: { days_old?: number }; Returns: number }
      cleanup_old_processes: { Args: { days_old?: number }; Returns: number }
      cleanup_old_snapshots: {
        Args: { p_days_old?: number; p_keep_count?: number }
        Returns: number
      }
      create_process_event: {
        Args: {
          p_event_category?: string
          p_event_data?: Json
          p_event_source?: string
          p_event_type: string
          p_process_id: string
        }
        Returns: string
      }
      create_user_subscription_record: {
        Args: { p_email: string; p_user_id: string }
        Returns: {
          addon_quantity: number
          cancel_at_period_end: boolean | null
          created_at: string | null
          current_period_end: string | null
          email: string | null
          is_privileged: boolean | null
          plan_tier_id: string | null
          status: Database["public"]["Enums"]["user_subscription_status"]
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          updated_at: string | null
          upgraded_to_org_id: string | null
          user_id: string
        }
        SetofOptions: {
          from: "*"
          to: "user_subscriptions"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      delete_article_version: {
        Args: { p_version_id: string }
        Returns: boolean
      }
      extract_image_placeholders: {
        Args: {
          article_content: string
          article_id_param?: string
          process_id?: string
        }
        Returns: undefined
      }
      get_article_version: {
        Args: { p_version_id: string }
        Returns: {
          article_id: string
          change_description: string
          content: string
          created_at: string
          is_current: boolean
          metadata: Json
          title: string
          user_id: string
          version_id: string
          version_number: number
        }[]
      }
      get_article_version_history: {
        Args: { p_article_id: string; p_limit?: number }
        Returns: {
          change_description: string
          created_at: string
          is_current: boolean
          metadata: Json
          title: string
          user_id: string
          version_id: string
          version_number: number
        }[]
      }
      get_available_snapshots: {
        Args: { p_process_id: string }
        Returns: {
          branch_id: string
          branch_name: string
          can_restore: boolean
          created_at: string
          is_active_branch: boolean
          is_current: boolean
          parent_snapshot_id: string
          snapshot_id: string
          step_category: string
          step_description: string
          step_index: number
          step_name: string
        }[]
      }
      get_current_article_version: {
        Args: { p_article_id: string }
        Returns: string
      }
      get_next_background_task: {
        Args: { task_types?: string[]; worker_id_param: string }
        Returns: string
      }
      get_process_recovery_info: {
        Args: { process_id: string }
        Returns: {
          can_resume: boolean
          current_data: Json
          input_type: string
          resume_step: string
          waiting_for_input: boolean
        }[]
      }
      get_snapshot_details: { Args: { p_snapshot_id: string }; Returns: Json }
      has_active_access: { Args: { p_user_id: string }; Returns: boolean }
      increment_usage_if_allowed: {
        Args: { p_tracking_id: string }
        Returns: {
          new_count: number
          was_allowed: boolean
        }[]
      }
      mark_process_waiting_for_input: {
        Args: {
          p_input_type: string
          p_process_id: string
          p_timeout_minutes?: number
        }
        Returns: undefined
      }
      migrate_image_to_gcs: {
        Args: {
          gcs_path_param: string
          gcs_url_param: string
          image_id_param: string
        }
        Returns: undefined
      }
      navigate_to_version: {
        Args: { p_article_id: string; p_direction: string }
        Returns: string
      }
      replace_placeholder_with_image: {
        Args: {
          alt_text_param?: string
          article_id_param: string
          image_id_param: string
          image_url: string
          placeholder_id_param: string
        }
        Returns: undefined
      }
      resolve_user_input: {
        Args: { p_process_id: string; p_user_response: Json }
        Returns: undefined
      }
      restore_article_version: {
        Args: { p_create_new_version?: boolean; p_version_id: string }
        Returns: Json
      }
      restore_from_snapshot: {
        Args: { p_create_new_branch?: boolean; p_snapshot_id: string }
        Returns: Json
      }
      save_article_version: {
        Args: {
          p_article_id: string
          p_change_description?: string
          p_content: string
          p_max_versions?: number
          p_metadata?: Json
          p_title: string
          p_user_id: string
        }
        Returns: string
      }
      save_step_snapshot: {
        Args: {
          p_article_context: Json
          p_branch_id?: string
          p_process_id: string
          p_snapshot_metadata?: Json
          p_step_category?: string
          p_step_description?: string
          p_step_name: string
        }
        Returns: string
      }
      switch_to_branch: {
        Args: { p_branch_id: string; p_process_id: string }
        Returns: boolean
      }
      update_subscription_from_stripe: {
        Args: {
          p_cancel_at_period_end?: boolean
          p_current_period_end: string
          p_status: string
          p_stripe_customer_id: string
          p_stripe_subscription_id: string
          p_user_id: string
        }
        Returns: {
          addon_quantity: number
          cancel_at_period_end: boolean | null
          created_at: string | null
          current_period_end: string | null
          email: string | null
          is_privileged: boolean | null
          plan_tier_id: string | null
          status: Database["public"]["Enums"]["user_subscription_status"]
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          updated_at: string | null
          upgraded_to_org_id: string | null
          user_id: string
        }
        SetofOptions: {
          from: "*"
          to: "user_subscriptions"
          isOneToOne: true
          isSetofReturn: false
        }
      }
    }
    Enums: {
      generation_status:
        | "in_progress"
        | "user_input_required"
        | "paused"
        | "completed"
        | "error"
        | "cancelled"
        | "resuming"
        | "auto_progressing"
      invitation_status: "pending" | "accepted" | "declined" | "expired"
      organization_role: "owner" | "admin" | "member"
      step_type:
        | "keyword_analysis"
        | "persona_generation"
        | "theme_proposal"
        | "research_planning"
        | "research_execution"
        | "research_synthesis"
        | "outline_generation"
        | "section_writing"
        | "editing"
        | "custom"
      style_template_type:
        | "writing_tone"
        | "vocabulary"
        | "structure"
        | "branding"
        | "seo_focus"
        | "custom"
      subscription_status:
        | "trialing"
        | "active"
        | "canceled"
        | "incomplete"
        | "incomplete_expired"
        | "past_due"
        | "unpaid"
        | "paused"
      user_subscription_status:
        | "active"
        | "past_due"
        | "canceled"
        | "expired"
        | "none"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      generation_status: [
        "in_progress",
        "user_input_required",
        "paused",
        "completed",
        "error",
        "cancelled",
        "resuming",
        "auto_progressing",
      ],
      invitation_status: ["pending", "accepted", "declined", "expired"],
      organization_role: ["owner", "admin", "member"],
      step_type: [
        "keyword_analysis",
        "persona_generation",
        "theme_proposal",
        "research_planning",
        "research_execution",
        "research_synthesis",
        "outline_generation",
        "section_writing",
        "editing",
        "custom",
      ],
      style_template_type: [
        "writing_tone",
        "vocabulary",
        "structure",
        "branding",
        "seo_focus",
        "custom",
      ],
      subscription_status: [
        "trialing",
        "active",
        "canceled",
        "incomplete",
        "incomplete_expired",
        "past_due",
        "unpaid",
        "paused",
      ],
      user_subscription_status: [
        "active",
        "past_due",
        "canceled",
        "expired",
        "none",
      ],
    },
  },
} as const
