create table if not exists public.company_memory (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete cascade,
  scope_type text not null check (scope_type in ('org', 'user')),
  content_json jsonb not null default '{"schema_version":1,"company_name":"","site_name":"","site_url":"","language":"ja","business_summary":"","company_positioning":"","site_positioning":"","core_services":[],"strengths":[],"target_customers":[],"brand_voice":[],"avoid_expressions":[],"preferred_messages":[],"style_rules":[],"primary_post_types":[],"primary_categories":[],"site_operational_notes":[]}'::jsonb,
  content_md text null,
  schema_version integer not null default 1,
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint company_memory_scope_org_user_chk
    check (
      (scope_type = 'org' and organization_id is not null)
      or (scope_type = 'user' and organization_id is null)
    )
);

comment on table public.company_memory is 'ブログ生成で毎回参照する会社共通メモ';
comment on column public.company_memory.scope_type is 'org または user';
comment on column public.company_memory.content_json is 'company memory の canonical JSON';
comment on column public.company_memory.content_md is '将来の表示用・編集用・エクスポート用Markdown。v1では未使用だが、Markdownベースの参照文脈にも転用できるよう保持する';
comment on column public.company_memory.schema_version is 'content_json の schema version';
comment on column public.company_memory.version is '楽観ロック用 version';

create unique index if not exists uq_company_memory_org_scope
  on public.company_memory (organization_id)
  where scope_type = 'org';

create unique index if not exists uq_company_memory_user_scope
  on public.company_memory (user_id)
  where scope_type = 'user';

create index if not exists idx_company_memory_org on public.company_memory (organization_id);
create index if not exists idx_company_memory_user on public.company_memory (user_id);

create or replace trigger update_company_memory_updated_at
before update on public.company_memory
for each row execute function public.update_updated_at_column();

alter table public.company_memory enable row level security;

drop policy if exists "Service role has full access to company_memory" on public.company_memory;
create policy "Service role has full access to company_memory"
  on public.company_memory
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
