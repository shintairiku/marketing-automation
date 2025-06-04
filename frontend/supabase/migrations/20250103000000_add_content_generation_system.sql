-- コンテンツ生成システム用のデータベーステーブル
-- 作成日: 2025-01-03
-- 目的: 記事生成、SerpAPI分析、ペルソナ管理、リサーチ結果などを保存

-- 1. 企業・組織情報テーブル（組織対応版）
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id TEXT, -- 組織所有の場合（後でFKを追加）
    name TEXT NOT NULL,
    description TEXT,
    style_guide TEXT, -- 文体・トンマナガイド
    industry TEXT, -- 業界
    website_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 個人所有または組織所有のどちらか一方のみ
    CONSTRAINT check_company_ownership CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL)
    )
);

-- 2. 記事生成プロジェクト管理（組織対応版）
CREATE TABLE article_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id TEXT, -- 組織所有の場合（後でFKを追加）
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft', -- draft, generating, completed, failed, cancelled
    initial_keywords TEXT[] NOT NULL,
    target_age_group TEXT, -- 10代, 20代, etc.
    persona_type TEXT, -- 主婦, 学生, 社会人, etc.
    custom_persona TEXT,
    target_length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 個人所有または組織所有のどちらか一方のみ
    CONSTRAINT check_project_ownership CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL)
    )
);

-- 3. SerpAPIキーワード分析結果
CREATE TABLE serp_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    search_query TEXT NOT NULL,
    total_results INTEGER,
    average_article_length INTEGER,
    recommended_target_length INTEGER,
    main_themes TEXT[],
    common_headings TEXT[],
    content_gaps TEXT[],
    competitive_advantages TEXT[],
    user_intent_analysis TEXT,
    content_strategy_recommendations TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SerpAPI分析対象記事詳細
CREATE TABLE serp_analyzed_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serp_analysis_id UUID REFERENCES serp_analyses(id) ON DELETE CASCADE NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    headings TEXT[],
    content_preview TEXT,
    char_count INTEGER,
    image_count INTEGER,
    source_type TEXT, -- organic_result, related_question
    position INTEGER,
    question TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 生成されたペルソナ
CREATE TABLE generated_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    description TEXT NOT NULL,
    is_selected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. 生成されたテーマ案
CREATE TABLE generated_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT[],
    is_selected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. リサーチ計画
CREATE TABLE research_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    topic TEXT NOT NULL,
    status TEXT DEFAULT 'draft', -- draft, approved, executing, completed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- リサーチクエリ
CREATE TABLE research_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_plan_id UUID REFERENCES research_plans(id) ON DELETE CASCADE NOT NULL,
    query TEXT NOT NULL,
    focus TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, executing, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- リサーチ結果
CREATE TABLE research_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_query_id UUID REFERENCES research_queries(id) ON DELETE CASCADE NOT NULL,
    summary TEXT NOT NULL,
    detailed_findings JSONB, -- SourceSnippet[]のJSON配列
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 統合リサーチレポート
CREATE TABLE research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    topic TEXT NOT NULL,
    overall_summary TEXT NOT NULL,
    key_points JSONB NOT NULL, -- KeyPoint[]のJSON配列
    interesting_angles TEXT[],
    all_sources TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. 記事アウトライン
CREATE TABLE article_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    suggested_tone TEXT NOT NULL,
    sections JSONB NOT NULL, -- OutlineSection[]のJSON配列
    status TEXT DEFAULT 'draft', -- draft, approved
    is_final BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- 記事セクション（生成された各セクション）
CREATE TABLE article_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    outline_id UUID REFERENCES article_outlines(id) ON DELETE CASCADE NOT NULL,
    section_index INTEGER NOT NULL,
    heading TEXT NOT NULL,
    html_content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. 最終記事
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    final_html_content TEXT NOT NULL,
    word_count INTEGER,
    seo_score INTEGER, -- 将来的なSEOスコア評価用
    published_url TEXT, -- 公開先URL（任意）
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE
);

-- 9. WebSocketセッション履歴（トラブルシューティング・継続処理用）
CREATE TABLE generation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES article_projects(id) ON DELETE CASCADE NOT NULL,
    session_id TEXT NOT NULL UNIQUE, -- バックエンドで生成されるセッションID
    trace_id TEXT, -- OpenAI Agents SDKトレーシング用ID
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    status TEXT NOT NULL DEFAULT 'connecting', -- connecting, active, completed, failed, disconnected
    current_step TEXT, -- 現在実行中のステップ
    websocket_connected BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- 生成過程のステップログ
CREATE TABLE generation_step_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES generation_sessions(id) ON DELETE CASCADE NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL, -- started, completed, failed, skipped
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB -- ステップ固有のデータ（エージェント出力、処理時間など）
);

-- インデックス作成（パフォーマンス向上のため）
CREATE INDEX idx_companies_user_id ON companies(user_id);
CREATE INDEX idx_article_projects_user_id ON article_projects(user_id);
CREATE INDEX idx_article_projects_status ON article_projects(status);
CREATE INDEX idx_serp_analyses_project_id ON serp_analyses(project_id);
CREATE INDEX idx_generated_personas_project_id ON generated_personas(project_id);
CREATE INDEX idx_generated_themes_project_id ON generated_themes(project_id);
CREATE INDEX idx_research_plans_project_id ON research_plans(project_id);
CREATE INDEX idx_research_queries_plan_id ON research_queries(research_plan_id);
CREATE INDEX idx_research_results_query_id ON research_results(research_query_id);
CREATE INDEX idx_article_outlines_project_id ON article_outlines(project_id);
CREATE INDEX idx_article_sections_project_id ON article_sections(project_id);
CREATE INDEX idx_articles_project_id ON articles(project_id);
CREATE INDEX idx_generation_sessions_project_id ON generation_sessions(project_id);
CREATE INDEX idx_generation_sessions_session_id ON generation_sessions(session_id);
CREATE INDEX idx_generation_step_logs_session_id ON generation_step_logs(session_id);

-- Row Level Security (RLS) の有効化
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE serp_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE serp_analyzed_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_outlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_step_logs ENABLE ROW LEVEL SECURITY;

-- RLS ポリシー作成

-- 企業テーブル: 個人所有または組織メンバーがアクセス可能（組織テーブル作成後に更新）
CREATE POLICY "Users can manage companies" ON companies
FOR ALL USING (auth.uid() = user_id);

-- プロジェクトテーブル: 個人所有または組織メンバーがアクセス可能（組織テーブル作成後に更新）
CREATE POLICY "Users can manage projects" ON article_projects
FOR ALL USING (auth.uid() = user_id);

-- 以下のテーブルは、関連するプロジェクトの所有者のみアクセス可能

CREATE POLICY "Users can access serp analyses for their projects" ON serp_analyses
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = serp_analyses.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access serp analyzed articles for their projects" ON serp_analyzed_articles
FOR ALL USING (EXISTS (
  SELECT 1 FROM serp_analyses 
  JOIN article_projects ON article_projects.id = serp_analyses.project_id
  WHERE serp_analyses.id = serp_analyzed_articles.serp_analysis_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access generated personas for their projects" ON generated_personas
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = generated_personas.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access generated themes for their projects" ON generated_themes
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = generated_themes.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access research plans for their projects" ON research_plans
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = research_plans.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access research queries for their projects" ON research_queries
FOR ALL USING (EXISTS (
  SELECT 1 FROM research_plans 
  JOIN article_projects ON article_projects.id = research_plans.project_id
  WHERE research_plans.id = research_queries.research_plan_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access research results for their projects" ON research_results
FOR ALL USING (EXISTS (
  SELECT 1 FROM research_queries 
  JOIN research_plans ON research_plans.id = research_queries.research_plan_id
  JOIN article_projects ON article_projects.id = research_plans.project_id
  WHERE research_queries.id = research_results.research_query_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access research reports for their projects" ON research_reports
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = research_reports.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access article outlines for their projects" ON article_outlines
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = article_outlines.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access article sections for their projects" ON article_sections
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = article_sections.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access articles for their projects" ON articles
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = articles.project_id 
  AND article_projects.user_id = auth.uid()
));

CREATE POLICY "Users can access generation sessions for their projects" ON generation_sessions
FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access generation step logs for their sessions" ON generation_step_logs
FOR ALL USING (EXISTS (
  SELECT 1 FROM generation_sessions 
  WHERE generation_sessions.id = generation_step_logs.session_id 
  AND generation_sessions.user_id = auth.uid()
));

-- 自動更新トリガー（updated_at フィールド用）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_article_projects_updated_at BEFORE UPDATE ON article_projects
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- リアルタイム機能の有効化（必要に応じて）
-- 以下のテーブルを Supabase リアルタイム機能で使用する場合はコメントアウトを外す
/*
ALTER PUBLICATION supabase_realtime ADD TABLE article_projects;
ALTER PUBLICATION supabase_realtime ADD TABLE generation_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE generation_step_logs;
*/