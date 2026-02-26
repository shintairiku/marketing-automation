\set ON_ERROR_STOP on

-- Usage:
--   psql "$DB_URL" -v base_pid="$PID" -f test/blog_memory_seed/load_seed_to_local.sql
--
-- Assumes CSV files already exist:
--   test/blog_memory_seed/blog_memory_meta_seed.csv
--   test/blog_memory_seed/blog_memory_items_seed.csv

create temp table tmp_memory_meta_seed (
  seed_no int not null,
  title text not null,
  short_summary text not null,
  user_prompt text not null,
  reference_url text,
  topic text,
  audience text
);

create temp table tmp_memory_items_seed (
  seed_no int not null,
  role text not null,
  content text not null
);

\copy tmp_memory_meta_seed from 'test/blog_memory_seed/blog_memory_meta_seed.csv' with (format csv, header true, encoding 'UTF8')
\copy tmp_memory_items_seed from 'test/blog_memory_seed/blog_memory_items_seed.csv' with (format csv, header true, encoding 'UTF8')

create temp table tmp_seed_process_map (
  seed_no int primary key,
  process_id uuid not null
);

with src as (
  select user_id, organization_id, wordpress_site_id
  from public.blog_generation_state
  where id = :'base_pid'::uuid
),
ins as (
  insert into public.blog_generation_state (
    id,
    user_id,
    organization_id,
    wordpress_site_id,
    status,
    current_step_name,
    progress_percentage,
    is_waiting_for_input,
    blog_context,
    user_prompt,
    reference_url,
    uploaded_images,
    realtime_channel,
    created_at,
    updated_at
  )
  select
    gen_random_uuid() as id,
    src.user_id,
    src.organization_id,
    src.wordpress_site_id,
    'completed',
    'seed-data',
    100,
    false,
    jsonb_build_object(
      'seed_no', m.seed_no,
      'topic', m.topic,
      'audience', m.audience
    ),
    m.user_prompt,
    m.reference_url,
    '[]'::jsonb,
    'blog_generation:' || gen_random_uuid()::text,
    now() - (m.seed_no || ' hours')::interval,
    now() - (m.seed_no || ' hours')::interval
  from src
  cross join tmp_memory_meta_seed m
  returning id, (blog_context->>'seed_no')::int as seed_no
)
insert into tmp_seed_process_map(seed_no, process_id)
select seed_no, id
from ins;

insert into public.blog_memory_meta (
  process_id,
  user_id,
  organization_id,
  scope_type,
  draft_post_id,
  title,
  short_summary,
  embedding_input,
  updated_at
)
select
  map.process_id,
  s.user_id,
  s.organization_id,
  case when s.organization_id is null then 'user' else 'org' end as scope_type,
  null::int,
  m.title,
  m.short_summary,
  m.title || E'\n\n' || m.short_summary,
  now() - (m.seed_no || ' hours')::interval
from tmp_memory_meta_seed m
join tmp_seed_process_map map
  on map.seed_no = m.seed_no
join public.blog_generation_state s
  on s.id = map.process_id;

insert into public.blog_memory_items (
  process_id,
  user_id,
  organization_id,
  scope_type,
  role,
  content,
  created_at
)
select
  map.process_id,
  s.user_id,
  s.organization_id,
  case when s.organization_id is null then 'user' else 'org' end as scope_type,
  i.role,
  case
    when i.role = 'tool_result' then replace(i.content, '__PROCESS_ID__', map.process_id::text)
    else i.content
  end as content,
  now() - (i.seed_no || ' hours')::interval
from tmp_memory_items_seed i
join tmp_seed_process_map map
  on map.seed_no = i.seed_no
join public.blog_generation_state s
  on s.id = map.process_id;

select
  (select count(*) from tmp_seed_process_map) as inserted_processes,
  (select count(*) from public.blog_memory_meta where process_id in (select process_id from tmp_seed_process_map)) as inserted_meta,
  (select count(*) from public.blog_memory_items where process_id in (select process_id from tmp_seed_process_map)) as inserted_items;
