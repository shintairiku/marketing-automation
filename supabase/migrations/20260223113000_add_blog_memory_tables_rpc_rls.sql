-- Blog Memory (phase1)
-- - tables: blog_memory_items, blog_memory_meta
-- - rls: scope-based ownership checks
-- - rpc: append/upsert/search/get-items

create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists public.blog_memory_items (
  id uuid primary key default gen_random_uuid(),
  process_id uuid not null references public.blog_generation_state(id) on delete cascade,
  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org', 'user')),
  role text not null check (
    role in (
      'user_input',
      'assistant_output',
      'tool_result',
      'source',
      'system_note',
      'final_summary'
    )
  ),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_blog_memory_items_process_created
  on public.blog_memory_items(process_id, created_at desc);

create index if not exists idx_blog_memory_items_scope_created
  on public.blog_memory_items(scope_type, organization_id, user_id, created_at desc);

create index if not exists idx_blog_memory_items_process_role_created
  on public.blog_memory_items(process_id, role, created_at desc);


create table if not exists public.blog_memory_meta (
  process_id uuid primary key references public.blog_generation_state(id) on delete cascade,
  user_id text not null,
  organization_id uuid null references public.organizations(id) on delete set null,
  scope_type text not null check (scope_type in ('org', 'user')),
  draft_post_id integer null,
  title text not null,
  short_summary text not null,
  embedding_input text not null,
  embedding vector(1536),
  embedding_updated_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists idx_blog_memory_meta_scope
  on public.blog_memory_meta(scope_type, organization_id, user_id);

create index if not exists idx_blog_memory_meta_embedding
  on public.blog_memory_meta using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);


alter table public.blog_memory_items enable row level security;
alter table public.blog_memory_meta enable row level security;

create or replace function public.is_owner_in_scope(
  p_scope_type text,
  p_org_id uuid,
  p_user_id text
) returns boolean
language sql
stable
as $$
  select case
    when p_scope_type = 'org' then exists (
      select 1
      from public.organization_members om
      where om.organization_id = p_org_id
        and om.user_id = auth.uid()::text
    )
    when p_scope_type = 'user' then p_user_id = auth.uid()::text
    else false
  end
$$;

drop policy if exists blog_memory_items_select_own_scope on public.blog_memory_items;
create policy blog_memory_items_select_own_scope
  on public.blog_memory_items for select
  using (public.is_owner_in_scope(scope_type, organization_id, user_id));

drop policy if exists blog_memory_items_insert_own_scope on public.blog_memory_items;
create policy blog_memory_items_insert_own_scope
  on public.blog_memory_items for insert
  with check (public.is_owner_in_scope(scope_type, organization_id, user_id));

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


create or replace function public.blog_memory_append_item(
  p_process_id uuid,
  p_role text,
  p_content text
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
  v_id uuid;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  if p_role = 'tool_result' then
    raise exception 'ROLE_TOOL_RESULT_FORBIDDEN';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_items(
    process_id, user_id, organization_id, scope_type, role, content
  ) values (
    p_process_id, v_user_id, v_org_id, v_scope, p_role, p_content
  )
  returning id into v_id;

  return v_id;
end;
$$;


create or replace function public.blog_memory_append_tool_result(
  p_process_id uuid,
  p_content text
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
  v_id uuid;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_items(
    process_id, user_id, organization_id, scope_type, role, content
  ) values (
    p_process_id, v_user_id, v_org_id, v_scope, 'tool_result', p_content
  )
  returning id into v_id;

  return v_id;
end;
$$;


create or replace function public.blog_memory_upsert_meta(
  p_process_id uuid,
  p_title text,
  p_short_summary text,
  p_embedding_input text,
  p_draft_post_id integer
) returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id text;
  v_org_id uuid;
  v_scope text;
begin
  select user_id, organization_id
    into v_user_id, v_org_id
  from public.blog_generation_state
  where id = p_process_id;

  if v_user_id is null then
    raise exception 'BLOG_PROCESS_NOT_FOUND';
  end if;

  v_scope := case when v_org_id is null then 'user' else 'org' end;

  insert into public.blog_memory_meta(
    process_id, user_id, organization_id, scope_type,
    draft_post_id, title, short_summary, embedding_input
  ) values (
    p_process_id, v_user_id, v_org_id, v_scope,
    p_draft_post_id, p_title, p_short_summary, p_embedding_input
  )
  on conflict (process_id) do update
    set draft_post_id = excluded.draft_post_id,
        title = excluded.title,
        short_summary = excluded.short_summary,
        embedding_input = excluded.embedding_input,
        updated_at = now();
end;
$$;


create or replace function public.blog_memory_search_meta(
  p_process_id uuid,
  p_query vector(1536),
  p_k int
) returns table(
  hit_process_id uuid,
  score double precision,
  draft_post_id integer,
  title text,
  short_summary text
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
  )
  select
    m.process_id as hit_process_id,
    (m.embedding <=> p_query) as score,
    m.draft_post_id,
    m.title,
    m.short_summary
  from public.blog_memory_meta m
  join src on (
    (src.scope_type = 'org' and m.scope_type = 'org' and m.organization_id = src.organization_id)
    or
    (src.scope_type = 'user' and m.scope_type = 'user' and m.user_id = src.user_id)
  )
  where m.embedding is not null
    and m.process_id <> p_process_id
  order by m.embedding <=> p_query
  limit p_k
$$;


create or replace function public.blog_memory_get_items(
  p_process_id uuid,
  p_roles text[],
  p_time_window_days int,
  p_limit int
) returns table(
  role text,
  content text,
  created_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  select role, content, created_at
  from public.blog_memory_items
  where process_id = p_process_id
    and (p_roles is null or role = any(p_roles))
    and (
      p_time_window_days is null
      or created_at >= now() - (p_time_window_days || ' days')::interval
    )
  order by created_at desc
  limit p_limit
$$;

