-- Performance indexes for hot query paths
-- Apply manually in Supabase SQL editor.

-- chat history and session listing
create index if not exists idx_chat_messages_user_created_desc
  on public.chat_messages(user_id, created_at desc);

create index if not exists idx_chat_messages_user_session_created_desc
  on public.chat_messages(user_id, session_id, created_at desc);

-- class membership approval lookup by student + status
create index if not exists idx_class_members_student_status
  on public.class_members(student_id, status);

-- class files lookup by class id + latest uploads
create index if not exists idx_class_files_class_uploaded_desc
  on public.class_files(class_id, uploaded_at desc);

-- uploads listing by user + recency
create index if not exists idx_uploads_user_uploaded_desc
  on public.uploads(user_id, uploaded_at desc);
