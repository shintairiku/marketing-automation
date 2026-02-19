-- =============================================================
-- SEED DATA
-- Required for the application to function correctly.
-- =============================================================

-- 1. Default Plan Tier
-- NOTE: stripe_price_id must be updated to the real Stripe Price ID after deployment.
--   UPDATE plan_tiers SET stripe_price_id = 'price_XXXXXX' WHERE id = 'default';
INSERT INTO plan_tiers (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount, display_order, is_active)
VALUES ('default', '標準プラン', 'PLACEHOLDER', 30, 20, 29800, 1, true)
ON CONFLICT (id) DO NOTHING;

-- 2. Default SEO Article Generation Flow Template
INSERT INTO article_generation_flows (id, name, description, is_template, user_id, organization_id)
VALUES (
  gen_random_uuid(),
  'Default SEO Article Generation',
  'Complete SEO article generation workflow with keyword analysis, persona development, research, and writing',
  true,
  null,
  null
)
ON CONFLICT DO NOTHING;

-- 3. Default Flow Steps (9 steps)
DO $$
DECLARE
  default_flow_id uuid;
BEGIN
  SELECT id INTO default_flow_id
  FROM article_generation_flows
  WHERE name = 'Default SEO Article Generation' AND is_template = true
  LIMIT 1;

  IF default_flow_id IS NULL THEN
    RAISE NOTICE 'Default flow template not found, skipping step insertion';
    RETURN;
  END IF;

  -- Only insert if no steps exist yet for this flow
  IF NOT EXISTS (SELECT 1 FROM flow_steps WHERE flow_id = default_flow_id) THEN
    INSERT INTO flow_steps (flow_id, step_order, step_type, agent_name, is_interactive, skippable) VALUES
      (default_flow_id, 1, 'keyword_analysis', 'serp_keyword_analysis_agent', false, false),
      (default_flow_id, 2, 'persona_generation', 'persona_generator_agent', true, false),
      (default_flow_id, 3, 'theme_proposal', 'theme_agent', true, false),
      (default_flow_id, 4, 'research_planning', 'research_planner_agent', true, false),
      (default_flow_id, 5, 'research_execution', 'researcher_agent', false, false),
      (default_flow_id, 6, 'research_synthesis', 'research_synthesizer_agent', false, false),
      (default_flow_id, 7, 'outline_generation', 'outline_agent', true, false),
      (default_flow_id, 8, 'section_writing', 'section_writer_agent', false, false),
      (default_flow_id, 9, 'editing', 'editor_agent', false, false);
  END IF;
END $$;
