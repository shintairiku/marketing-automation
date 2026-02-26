\set ON_ERROR_STOP on
\pset pager off

-- Latest 15 generation processes
select
  gs.id as process_id,
  gs.created_at,
  gs.status,
  gs.draft_post_id,
  left(coalesce(gs.user_prompt, ''), 80) as prompt_head
from public.blog_generation_state gs
order by gs.created_at desc
limit 15;

-- Memory meta status for latest 15
with latest as (
  select id, created_at
  from public.blog_generation_state
  order by created_at desc
  limit 15
)
select
  l.id as process_id,
  m.title,
  m.short_summary,
  (m.embedding is not null) as has_embedding,
  m.embedding_updated_at,
  m.updated_at
from latest l
left join public.blog_memory_meta m on m.process_id = l.id
order by l.created_at desc;

-- Role counts for latest 15
with latest as (
  select id
  from public.blog_generation_state
  order by created_at desc
  limit 15
)
select
  i.process_id,
  count(*) as total_items,
  count(*) filter (where i.role = 'user_input') as user_input_cnt,
  count(*) filter (where i.role = 'assistant_output') as assistant_output_cnt,
  count(*) filter (where i.role = 'source') as source_cnt,
  count(*) filter (where i.role = 'system_note') as system_note_cnt,
  count(*) filter (where i.role = 'final_summary') as final_summary_cnt,
  count(*) filter (where i.role = 'tool_result') as tool_result_cnt
from public.blog_memory_items i
where i.process_id in (select id from latest)
group by i.process_id
order by total_items desc, i.process_id;

-- Remaining rows without fresh embedding
select
  count(*) as remaining_unembedded
from public.blog_memory_meta
where embedding is null
   or embedding_updated_at is null
   or embedding_updated_at < updated_at;
