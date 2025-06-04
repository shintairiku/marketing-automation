export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      age_groups: {
        Row: {
          created_at: string | null
          id: string
          is_active: boolean | null
          max_age: number | null
          min_age: number | null
          name: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          max_age?: number | null
          min_age?: number | null
          name: string
        }
        Update: {
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          max_age?: number | null
          min_age?: number | null
          name?: string
        }
        Relationships: []
      }
      article_outlines: {
        Row: {
          created_at: string | null
          headings: Json
          id: string
          is_selected: boolean | null
          lead_text: string | null
          project_id: string
          theme_id: string | null
          user_modified_headings: Json | null
          user_modified_lead_text: string | null
        }
        Insert: {
          created_at?: string | null
          headings: Json
          id?: string
          is_selected?: boolean | null
          lead_text?: string | null
          project_id: string
          theme_id?: string | null
          user_modified_headings?: Json | null
          user_modified_lead_text?: string | null
        }
        Update: {
          created_at?: string | null
          headings?: Json
          id?: string
          is_selected?: boolean | null
          lead_text?: string | null
          project_id?: string
          theme_id?: string | null
          user_modified_headings?: Json | null
          user_modified_lead_text?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "article_outlines_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "article_outlines_theme_id_fkey"
            columns: ["theme_id"]
            isOneToOne: false
            referencedRelation: "article_themes"
            referencedColumns: ["id"]
          },
        ]
      }
      article_projects: {
        Row: {
          created_at: string | null
          id: string
          keyword: string
          research_query_count: number | null
          selected_persona_id: string | null
          selected_persona_type: string | null
          serp_analysis_id: string | null
          specific_persona_count: number | null
          status: string | null
          suggested_word_count: number | null
          target_age_group_id: string | null
          target_word_count: number | null
          theme_suggestion_count: number | null
          title: string
          updated_at: string | null
          use_company_info: boolean | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          keyword: string
          research_query_count?: number | null
          selected_persona_id?: string | null
          selected_persona_type?: string | null
          serp_analysis_id?: string | null
          specific_persona_count?: number | null
          status?: string | null
          suggested_word_count?: number | null
          target_age_group_id?: string | null
          target_word_count?: number | null
          theme_suggestion_count?: number | null
          title: string
          updated_at?: string | null
          use_company_info?: boolean | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          keyword?: string
          research_query_count?: number | null
          selected_persona_id?: string | null
          selected_persona_type?: string | null
          serp_analysis_id?: string | null
          specific_persona_count?: number | null
          status?: string | null
          suggested_word_count?: number | null
          target_age_group_id?: string | null
          target_word_count?: number | null
          theme_suggestion_count?: number | null
          title?: string
          updated_at?: string | null
          use_company_info?: boolean | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "article_projects_serp_analysis_id_fkey"
            columns: ["serp_analysis_id"]
            isOneToOne: false
            referencedRelation: "serp_analyses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "article_projects_target_age_group_id_fkey"
            columns: ["target_age_group_id"]
            isOneToOne: false
            referencedRelation: "age_groups"
            referencedColumns: ["id"]
          },
        ]
      }
      article_themes: {
        Row: {
          created_at: string | null
          description: string | null
          id: string
          is_selected: boolean | null
          project_id: string
          title: string
          user_modified_title: string | null
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          id?: string
          is_selected?: boolean | null
          project_id: string
          title: string
          user_modified_title?: string | null
        }
        Update: {
          created_at?: string | null
          description?: string | null
          id?: string
          is_selected?: boolean | null
          project_id?: string
          title?: string
          user_modified_title?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "article_themes_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
        ]
      }
      company_profiles: {
        Row: {
          business_description: string | null
          company_name: string | null
          contact_info: Json | null
          created_at: string | null
          id: string
          industry: string | null
          target_customers: string | null
          unique_selling_points: Json | null
          updated_at: string | null
          user_id: string
          website_url: string | null
        }
        Insert: {
          business_description?: string | null
          company_name?: string | null
          contact_info?: Json | null
          created_at?: string | null
          id?: string
          industry?: string | null
          target_customers?: string | null
          unique_selling_points?: Json | null
          updated_at?: string | null
          user_id: string
          website_url?: string | null
        }
        Update: {
          business_description?: string | null
          company_name?: string | null
          contact_info?: Json | null
          created_at?: string | null
          id?: string
          industry?: string | null
          target_customers?: string | null
          unique_selling_points?: Json | null
          updated_at?: string | null
          user_id?: string
          website_url?: string | null
        }
        Relationships: []
      }
      customers: {
        Row: {
          id: string
          stripe_customer_id: string | null
        }
        Insert: {
          id: string
          stripe_customer_id?: string | null
        }
        Update: {
          id?: string
          stripe_customer_id?: string | null
        }
        Relationships: []
      }
      default_personas: {
        Row: {
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          name: string
          sort_order: number | null
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          name: string
          sort_order?: number | null
        }
        Update: {
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          name?: string
          sort_order?: number | null
        }
        Relationships: []
      }
      generated_articles: {
        Row: {
          company_mentions: Json | null
          content: Json
          created_at: string | null
          external_links: Json | null
          full_content: string | null
          id: string
          includes_tables: boolean | null
          internal_links: Json | null
          lead_text: string
          meta_description: string | null
          outline_id: string
          project_id: string
          status: string | null
          title: string
          updated_at: string | null
          word_count: number | null
        }
        Insert: {
          company_mentions?: Json | null
          content: Json
          created_at?: string | null
          external_links?: Json | null
          full_content?: string | null
          id?: string
          includes_tables?: boolean | null
          internal_links?: Json | null
          lead_text: string
          meta_description?: string | null
          outline_id: string
          project_id: string
          status?: string | null
          title: string
          updated_at?: string | null
          word_count?: number | null
        }
        Update: {
          company_mentions?: Json | null
          content?: Json
          created_at?: string | null
          external_links?: Json | null
          full_content?: string | null
          id?: string
          includes_tables?: boolean | null
          internal_links?: Json | null
          lead_text?: string
          meta_description?: string | null
          outline_id?: string
          project_id?: string
          status?: string | null
          title?: string
          updated_at?: string | null
          word_count?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "generated_articles_outline_id_fkey"
            columns: ["outline_id"]
            isOneToOne: false
            referencedRelation: "article_outlines"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "generated_articles_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
        ]
      }
      generated_personas: {
        Row: {
          content: string
          created_at: string | null
          id: string
          is_selected: boolean | null
          project_id: string
          user_modified_content: string | null
        }
        Insert: {
          content: string
          created_at?: string | null
          id?: string
          is_selected?: boolean | null
          project_id: string
          user_modified_content?: string | null
        }
        Update: {
          content?: string
          created_at?: string | null
          id?: string
          is_selected?: boolean | null
          project_id?: string
          user_modified_content?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "generated_personas_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
        ]
      }
      generation_steps: {
        Row: {
          completed_at: string | null
          created_at: string | null
          error_message: string | null
          id: string
          project_id: string
          started_at: string | null
          status: string | null
          step_data: Json | null
          step_name: string
        }
        Insert: {
          completed_at?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          project_id: string
          started_at?: string | null
          status?: string | null
          step_data?: Json | null
          step_name: string
        }
        Update: {
          completed_at?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          project_id?: string
          started_at?: string | null
          status?: string | null
          step_data?: Json | null
          step_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "generation_steps_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
        ]
      }
      prices: {
        Row: {
          active: boolean | null
          currency: string | null
          description: string | null
          id: string
          interval: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count: number | null
          metadata: Json | null
          product_id: string | null
          trial_period_days: number | null
          type: Database["public"]["Enums"]["pricing_type"] | null
          unit_amount: number | null
        }
        Insert: {
          active?: boolean | null
          currency?: string | null
          description?: string | null
          id: string
          interval?: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count?: number | null
          metadata?: Json | null
          product_id?: string | null
          trial_period_days?: number | null
          type?: Database["public"]["Enums"]["pricing_type"] | null
          unit_amount?: number | null
        }
        Update: {
          active?: boolean | null
          currency?: string | null
          description?: string | null
          id?: string
          interval?: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count?: number | null
          metadata?: Json | null
          product_id?: string | null
          trial_period_days?: number | null
          type?: Database["public"]["Enums"]["pricing_type"] | null
          unit_amount?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "prices_product_id_fkey"
            columns: ["product_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
        ]
      }
      products: {
        Row: {
          active: boolean | null
          description: string | null
          id: string
          image: string | null
          metadata: Json | null
          name: string | null
        }
        Insert: {
          active?: boolean | null
          description?: string | null
          id: string
          image?: string | null
          metadata?: Json | null
          name?: string | null
        }
        Update: {
          active?: boolean | null
          description?: string | null
          id?: string
          image?: string | null
          metadata?: Json | null
          name?: string | null
        }
        Relationships: []
      }
      research_queries: {
        Row: {
          created_at: string | null
          heading_title: string
          id: string
          outline_id: string | null
          project_id: string
          query_text: string
          research_elements: Json | null
          research_results: Json | null
          search_intent: string | null
          source_links: Json | null
        }
        Insert: {
          created_at?: string | null
          heading_title: string
          id?: string
          outline_id?: string | null
          project_id: string
          query_text: string
          research_elements?: Json | null
          research_results?: Json | null
          search_intent?: string | null
          source_links?: Json | null
        }
        Update: {
          created_at?: string | null
          heading_title?: string
          id?: string
          outline_id?: string | null
          project_id?: string
          query_text?: string
          research_elements?: Json | null
          research_results?: Json | null
          search_intent?: string | null
          source_links?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "research_queries_outline_id_fkey"
            columns: ["outline_id"]
            isOneToOne: false
            referencedRelation: "article_outlines"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "research_queries_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "article_projects"
            referencedColumns: ["id"]
          },
        ]
      }
      scraped_articles: {
        Row: {
          content_length: number | null
          headings: Json | null
          id: string
          image_count: number | null
          is_from_related_question: boolean | null
          position: number | null
          related_question: string | null
          scraped_at: string | null
          serp_analysis_id: string | null
          title: string | null
          url: string
        }
        Insert: {
          content_length?: number | null
          headings?: Json | null
          id?: string
          image_count?: number | null
          is_from_related_question?: boolean | null
          position?: number | null
          related_question?: string | null
          scraped_at?: string | null
          serp_analysis_id?: string | null
          title?: string | null
          url: string
        }
        Update: {
          content_length?: number | null
          headings?: Json | null
          id?: string
          image_count?: number | null
          is_from_related_question?: boolean | null
          position?: number | null
          related_question?: string | null
          scraped_at?: string | null
          serp_analysis_id?: string | null
          title?: string | null
          url?: string
        }
        Relationships: [
          {
            foreignKeyName: "scraped_articles_serp_analysis_id_fkey"
            columns: ["serp_analysis_id"]
            isOneToOne: false
            referencedRelation: "serp_analyses"
            referencedColumns: ["id"]
          },
        ]
      }
      serp_analyses: {
        Row: {
          average_word_count: number | null
          created_at: string | null
          id: string
          keyword: string
          organic_results: Json | null
          related_questions: Json | null
          search_results: Json
          user_id: string
        }
        Insert: {
          average_word_count?: number | null
          created_at?: string | null
          id?: string
          keyword: string
          organic_results?: Json | null
          related_questions?: Json | null
          search_results: Json
          user_id: string
        }
        Update: {
          average_word_count?: number | null
          created_at?: string | null
          id?: string
          keyword?: string
          organic_results?: Json | null
          related_questions?: Json | null
          search_results?: Json
          user_id?: string
        }
        Relationships: []
      }
      subscriptions: {
        Row: {
          cancel_at: string | null
          cancel_at_period_end: boolean | null
          canceled_at: string | null
          created: string
          current_period_end: string
          current_period_start: string
          ended_at: string | null
          id: string
          metadata: Json | null
          price_id: string | null
          quantity: number | null
          status: Database["public"]["Enums"]["subscription_status"] | null
          trial_end: string | null
          trial_start: string | null
          user_id: string
        }
        Insert: {
          cancel_at?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          created?: string
          current_period_end?: string
          current_period_start?: string
          ended_at?: string | null
          id: string
          metadata?: Json | null
          price_id?: string | null
          quantity?: number | null
          status?: Database["public"]["Enums"]["subscription_status"] | null
          trial_end?: string | null
          trial_start?: string | null
          user_id: string
        }
        Update: {
          cancel_at?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          created?: string
          current_period_end?: string
          current_period_start?: string
          ended_at?: string | null
          id?: string
          metadata?: Json | null
          price_id?: string | null
          quantity?: number | null
          status?: Database["public"]["Enums"]["subscription_status"] | null
          trial_end?: string | null
          trial_start?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "subscriptions_price_id_fkey"
            columns: ["price_id"]
            isOneToOne: false
            referencedRelation: "prices"
            referencedColumns: ["id"]
          },
        ]
      }
      user_personas: {
        Row: {
          created_at: string | null
          description: string
          id: string
          name: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          description: string
          id?: string
          name: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          description?: string
          id?: string
          name?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      users: {
        Row: {
          avatar_url: string | null
          billing_address: Json | null
          full_name: string | null
          id: string
          payment_method: Json | null
        }
        Insert: {
          avatar_url?: string | null
          billing_address?: Json | null
          full_name?: string | null
          id: string
          payment_method?: Json | null
        }
        Update: {
          avatar_url?: string | null
          billing_address?: Json | null
          full_name?: string | null
          id?: string
          payment_method?: Json | null
        }
        Relationships: []
      }
      organizations: {
        Row: {
          id: string
          name: string | null
          slug: string | null
          owner_user_id: string
          max_seats: number
          used_seats: number
          billing_email: string | null
          subscription_status: string
          stripe_customer_id: string | null
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          id: string
          name?: string | null
          slug?: string | null
          owner_user_id: string
          max_seats?: number
          used_seats?: number
          billing_email?: string | null
          subscription_status?: string
          stripe_customer_id?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          id?: string
          name?: string | null
          slug?: string | null
          owner_user_id?: string
          max_seats?: number
          used_seats?: number
          billing_email?: string | null
          subscription_status?: string
          stripe_customer_id?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      organization_memberships: {
        Row: {
          id: string
          organization_id: string
          user_id: string
          role: string
          status: string
          invited_by: string | null
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          id?: string
          organization_id: string
          user_id: string
          role?: string
          status?: string
          invited_by?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          id?: string
          organization_id?: string
          user_id?: string
          role?: string
          status?: string
          invited_by?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "organization_memberships_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          }
        ]
      }
      organization_invitations: {
        Row: {
          id: string
          organization_id: string
          email: string
          role: string
          invited_by: string
          invitation_token: string
          status: string
          expires_at: string
          invited_at: string | null
          accepted_at: string | null
          created_at: string | null
        }
        Insert: {
          id?: string
          organization_id: string
          email: string
          role?: string
          invited_by: string
          invitation_token: string
          status?: string
          expires_at: string
          invited_at?: string | null
          accepted_at?: string | null
          created_at?: string | null
        }
        Update: {
          id?: string
          organization_id?: string
          email?: string
          role?: string
          invited_by?: string
          invitation_token?: string
          status?: string
          expires_at?: string
          invited_at?: string | null
          accepted_at?: string | null
          created_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "organization_invitations_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          }
        ]
      }
      organization_settings: {
        Row: {
          organization_id: string
          default_company_name: string | null
          default_company_description: string | null
          default_style_guide: string | null
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          organization_id: string
          default_company_name?: string | null
          default_company_description?: string | null
          default_style_guide?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          organization_id?: string
          default_company_name?: string | null
          default_company_description?: string | null
          default_style_guide?: string | null
          created_at?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "organization_settings_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: true
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          }
        ]
      }
      unified_subscriptions: {
        Row: {
          id: string
          user_id: string | null
          organization_id: string | null
          subscription_type: string
          plan_tier: string
          stripe_customer_id: string
          stripe_subscription_id: string
          stripe_price_id: string
          seat_quantity: number | null
          seat_price_per_unit: number | null
          status: string
          current_period_start: string | null
          current_period_end: string | null
          cancel_at_period_end: boolean | null
          canceled_at: string | null
          trial_start: string | null
          trial_end: string | null
          monthly_article_limit: number
          monthly_articles_used: number
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          id?: string
          user_id?: string | null
          organization_id?: string | null
          subscription_type: string
          plan_tier: string
          stripe_customer_id: string
          stripe_subscription_id: string
          stripe_price_id: string
          seat_quantity?: number | null
          seat_price_per_unit?: number | null
          status?: string
          current_period_start?: string | null
          current_period_end?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          trial_start?: string | null
          trial_end?: string | null
          monthly_article_limit?: number
          monthly_articles_used?: number
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          id?: string
          user_id?: string | null
          organization_id?: string | null
          subscription_type?: string
          plan_tier?: string
          stripe_customer_id?: string
          stripe_subscription_id?: string
          stripe_price_id?: string
          seat_quantity?: number | null
          seat_price_per_unit?: number | null
          status?: string
          current_period_start?: string | null
          current_period_end?: string | null
          cancel_at_period_end?: boolean | null
          canceled_at?: string | null
          trial_start?: string | null
          trial_end?: string | null
          monthly_article_limit?: number
          monthly_articles_used?: number
          created_at?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "unified_subscriptions_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          }
        ]
      }
      usage_tracking: {
        Row: {
          id: string
          user_id: string
          organization_id: string | null
          resource_type: string
          usage_count: number
          billing_period_start: string
          billing_period_end: string
          created_at: string | null
        }
        Insert: {
          id?: string
          user_id: string
          organization_id?: string | null
          resource_type: string
          usage_count?: number
          billing_period_start: string
          billing_period_end: string
          created_at?: string | null
        }
        Update: {
          id?: string
          user_id?: string
          organization_id?: string | null
          resource_type?: string
          usage_count?: number
          billing_period_start?: string
          billing_period_end?: string
          created_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "usage_tracking_organization_id_fkey"
            columns: ["organization_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          }
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      pricing_plan_interval: "day" | "week" | "month" | "year"
      pricing_type: "one_time" | "recurring"
      subscription_status:
        | "trialing"
        | "active"
        | "canceled"
        | "incomplete"
        | "incomplete_expired"
        | "past_due"
        | "unpaid"
        | "paused"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
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
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
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
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
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
    | { schema: keyof Database },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      pricing_plan_interval: ["day", "week", "month", "year"],
      pricing_type: ["one_time", "recurring"],
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
    },
  },
} as const
