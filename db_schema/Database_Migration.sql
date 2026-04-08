-- Supabase SQL Schema for Pixel Audit System
-- Run this in Supabase SQL Editor
-- WARNING: Only run once. If tables already exist, this will NOT destroy data.

-- ══════════════════════════════════════════════════════════════════════
-- 1. Audit Logs Table  (primary: stores CID + request_id from IPFS)
-- ══════════════════════════════════════════════════════════════════════

CREATE TABLE public.audit_logs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  cid text NOT NULL,
  request_id text NOT NULL,
  user_id text DEFAULT 'default_user'::text,
  status text NOT NULL,
  description text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT audit_logs_pkey PRIMARY KEY (id)
);
