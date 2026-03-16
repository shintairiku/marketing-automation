-- Blog Memory refactor for memory-only spec
-- - blog_memory_items(row-based) -> blog_memory_detail(memory_json)
-- - short_summary -> summary
-- - add post_type/category_ids/created_at to meta
-- - replace search RPC
-- - detail stores only auto-captured data in memory_json

create extension if not exists pgcrypto;
create extension if not exists vector;

create or replace function public.is_owner_in_scope(
  p_scope_type text,
  p_organization_id uuid,
  p_user_id text
) returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select case
    when coalesce((current_setting('request.jwt.claims', true))::json ->> 'role', '') = 'service_role' then true
    when p_scope_type = 'org' then exists (
      select 1
      from public.organization_members om
      where om.organization_id = p_organization_id
        and om.user_id = ((current_setting('request.jwt.claims', true))::json ->> 'sub')
    )
    else p_user_id = ((current_setting('request.jwt.claims', true))::json ->> 'sub')
  end;
$$;

-- blog_memory_meta adjustments

create table if not exists public.blog_memory_meta (
  process_id uuid primary key references public.blog_generation_state(id) on delete cascade,
  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org', 'user')),
  draft_post_id integer null,
  title text not null,
  summary text not null,
  post_type text null,
  category_ids integer[] not null default '{}'::integer[],
  embedding_input text not null default '',
  embedding vector(1536),
  embedding_updated_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'blog_memory_meta'
      and column_name = 'short_summary'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'blog_memory_meta'
      and column_name = 'summary'
  ) then
    execute 'alter table public.blog_memory_meta rename column short_summary to summary';
  end if;
end
$$;

alter table if exists public.blog_memory_meta
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists post_type text,
  add column if not exists category_ids integer[] not null default '{}'::integer[];

update public.blog_memory_meta
set category_ids = '{}'::integer[]
where category_ids is null;

create index if not exists idx_blog_memory_meta_post_type
  on public.blog_memory_meta(post_type);

create index if not exists idx_blog_memory_meta_category_ids_gin
  on public.blog_memory_meta using gin(category_ids);

create index if not exists idx_blog_memory_meta_scope
  on public.blog_memory_meta(scope_type, organization_id, user_id);

create index if not exists idx_blog_memory_meta_embedding
  on public.blog_memory_meta using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

alter table public.blog_memory_meta enable row level security;

drop policy if exists blog_memory_meta_select_own_scope on public.blog_memory_meta;
create policy blog_memory_meta_select_own_scope
  on public.blog_memory_meta for select
  using (public.is_owner_in_scope(scope_type, organization_id, user_id));

drop policy if exists blog_memory_meta_insert_own_scope on public.blog_memory_meta;
create policy blog_memory_meta_insert_own_scope
  on public.blog_memory_meta for insert
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

drop policy if exists blog_memory_meta_update_own_scope on public.blog_memory_meta;
create policy blog_memory_meta_update_own_scope
  on public.blog_memory_meta for update
  using (public.is_owner_in_scope(scope_type, organization_id, user_id))
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

-- detail table
create table if not exists public.blog_memory_detail (
  process_id uuid primary key references public.blog_generation_state(id) on delete cascade,
  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org', 'user')),
  memory_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_blog_memory_detail_scope
  on public.blog_memory_detail(scope_type, organization_id, user_id);

alter table public.blog_memory_detail enable row level security;

drop policy if exists blog_memory_detail_select_own_scope on public.blog_memory_detail;
create policy blog_memory_detail_select_own_scope
  on public.blog_memory_detail for select
  using (public.is_owner_in_scope(scope_type, organization_id, user_id));

drop policy if exists blog_memory_detail_insert_own_scope on public.blog_memory_detail;
create policy blog_memory_detail_insert_own_scope
  on public.blog_memory_detail for insert
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

drop policy if exists blog_memory_detail_update_own_scope on public.blog_memory_detail;
create policy blog_memory_detail_update_own_scope
  on public.blog_memory_detail for update
  using (public.is_owner_in_scope(scope_type, organization_id, user_id))
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

-- migrate existing row-based detail if present

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = 'blog_memory_items'
  ) then
    insert into public.blog_memory_detail (
      process_id,
      user_id,
      organization_id,
      scope_type,
      memory_json,
      created_at,
      updated_at
    )
    with grouped as (
      select
        i.process_id,
        (array_agg(i.user_id order by i.created_at desc))[1] as user_id,
        (array_agg(i.organization_id order by i.created_at desc) filter (where i.organization_id is not null))[1] as organization_id,
        (array_agg(i.scope_type order by i.created_at desc))[1] as scope_type,
        min(i.created_at) as created_at,
        max(i.created_at) as updated_at,
        (array_agg(i.content order by i.created_at asc) filter (where i.role = 'user_input'))[1] as user_input,
        (array_agg(i.content order by i.created_at desc) filter (where i.role = 'final_summary'))[1] as summary,
        coalesce(
          jsonb_agg(
            jsonb_build_object(
              'question', null,
              'answer', i.content,
              'payload', jsonb_build_object('migrated_from', 'qa')
            )
            order by i.created_at asc
          ) filter (where i.role = 'qa'),
          '[]'::jsonb
        ) as qa_json,
        coalesce(
          jsonb_agg(
            jsonb_build_object(
              'tool_name', 'legacy_tool_result',
              'summary', i.content,
              'created_at', i.created_at
            )
            order by i.created_at asc
          ) filter (where i.role = 'tool_result'),
          '[]'::jsonb
        ) as tool_results_json,
        '[]'::jsonb as references_json
      from public.blog_memory_items i
      group by i.process_id
    )
    select
      g.process_id,
      g.user_id,
      g.organization_id,
      coalesce(g.scope_type, case when g.organization_id is null then 'user' else 'org' end),
      jsonb_build_object(
        'user_input', g.user_input,
        'qa', g.qa_json,
        'summary', g.summary,
        'note', null,
        'tool_results', g.tool_results_json,
        'execution_trace', '{}'::jsonb,
        'references', g.references_json
      ),
      g.created_at,
      g.updated_at
    from grouped g
    on conflict (process_id) do nothing;
  end if;
end
$$;

-- old row-based APIs are obsolete in memory-only design
drop function if exists public.blog_memory_append_item(uuid, text, text);
drop function if exists public.blog_memory_append_tool_result(uuid, text);
drop function if exists public.blog_memory_get_items(uuid, text[], integer, integer);
drop table if exists public.blog_memory_items cascade;

create or replace function public.blog_memory_upsert_meta(
  p_process_id uuid,
  p_title text,
  p_summary text,
  p_embedding_input text,
  p_draft_post_id integer,
  p_post_type text default null,
  p_category_ids integer[] default null
) returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
  v_category_ids integer[];
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;
  select coalesce(array_agg(distinct x order by x), '{}'::integer[])
    into v_category_ids
  from unnest(coalesce(p_category_ids, '{}'::integer[])) as t(x);

  insert into public.blog_memory_meta(
    process_id,
    user_id,
    organization_id,
    scope_type,
    draft_post_id,
    title,
    summary,
    post_type,
    category_ids,
    embedding_input,
    created_at,
    updated_at
  ) values (
    p_process_id,
    v_user_id,
    v_org_id,
    v_scope,
    p_draft_post_id,
    p_title,
    p_summary,
    p_post_type,
    v_category_ids,
    p_embedding_input,
    now(),
    now()
  )
  on conflict (process_id) do update
    set draft_post_id = excluded.draft_post_id,
        title = excluded.title,
        summary = excluded.summary,
        post_type = excluded.post_type,
        category_ids = excluded.category_ids,
        embedding_input = excluded.embedding_input,
        updated_at = now();
end;
$$;

create or replace function public.blog_memory_search_meta(
  p_process_id uuid,
  p_query vector(1536),
  p_k int,
  p_post_type text default null,
  p_category_ids integer[] default null,
  p_time_window_days int default 365
) returns table(
  hit_process_id uuid,
  score double precision,
  draft_post_id integer,
  title text,
  summary text,
  post_type text,
  category_ids integer[]
)
language sql
security definer
set search_path = public
as $$
  with src as (
    select
      user_id,
      organization_id,
      case when organization_id is null then 'user' else 'org' end as scope_type
    from public.blog_generation_state
    where id = p_process_id
  ),
  normalized as (
    select coalesce(array_agg(distinct x order by x), '{}'::integer[]) as category_ids
    from unnest(coalesce(p_category_ids, '{}'::integer[])) as t(x)
  ),
  scoped as (
    select
      m.process_id,
      m.draft_post_id,
      m.title,
      m.summary,
      m.post_type,
      m.category_ids,
      m.updated_at,
      (m.embedding <=> p_query) as score,
      cardinality(
        array(
          select unnest(coalesce(m.category_ids, '{}'::integer[]))
          intersect
          select unnest((select category_ids from normalized))
        )
      ) as overlap_count,
      case
        when p_post_type is not null
          and m.post_type = p_post_type
          and cardinality((select category_ids from normalized)) > 0
          and coalesce(m.category_ids, '{}'::integer[]) = (select category_ids from normalized)
          then 1
        when p_post_type is not null
          and m.post_type = p_post_type
          and cardinality(
            array(
              select unnest(coalesce(m.category_ids, '{}'::integer[]))
              intersect
              select unnest((select category_ids from normalized))
            )
          ) > 0
          then 2
        when p_post_type is not null
          and m.post_type = p_post_type
          then 3
        else 4
      end as priority
    from public.blog_memory_meta m
    cross join src
    where m.process_id <> p_process_id
      and (
        (src.scope_type = 'org' and m.scope_type = 'org' and m.organization_id = src.organization_id)
        or
        (src.scope_type = 'user' and m.scope_type = 'user' and m.user_id = src.user_id)
      )
      and m.embedding is not null
      and (p_time_window_days is null or m.updated_at >= now() - make_interval(days => p_time_window_days))
  )
  select
    process_id as hit_process_id,
    score,
    draft_post_id,
    title,
    summary,
    post_type,
    category_ids
  from scoped
  order by priority asc, overlap_count desc, score asc, updated_at desc nulls last
  limit greatest(p_k, 1);
$$;
