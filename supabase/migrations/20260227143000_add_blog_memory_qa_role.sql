-- blog_memory_items.role に qa を追加

do $$
declare
  r record;
begin
  for r in
    select conname
    from pg_constraint
    where conrelid = 'public.blog_memory_items'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%role%'
  loop
    execute format(
      'alter table public.blog_memory_items drop constraint %I',
      r.conname
    );
  end loop;
end
$$;

alter table public.blog_memory_items
  add constraint blog_memory_items_role_check
  check (
    role in (
      'user_input',
      'qa',
      'assistant_output',
      'tool_result',
      'source',
      'system_note',
      'final_summary'
    )
  );
