-- =============================================================================
-- RLS (Row Level Security) Fix for Supabase
-- This script enables RLS and creates policies for the 'anon' role
-- Run this in Supabase SQL Editor
-- =============================================================================

-- -----------------------------------------------------------------------------
-- STEP 1: Enable RLS on suppliers table
-- -----------------------------------------------------------------------------
ALTER TABLE IF EXISTS public.suppliers ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- STEP 2: Create policy to allow 'anon' role to SELECT from suppliers
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow anonymous SELECT on suppliers" ON public.suppliers;

CREATE POLICY "Allow anonymous SELECT on suppliers" ON public.suppliers
    FOR SELECT
    TO anon
    USING (true);

-- -----------------------------------------------------------------------------
-- STEP 3: Create policy to allow 'anon' role to INSERT into suppliers
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow anonymous INSERT on suppliers" ON public.suppliers;

CREATE POLICY "Allow anonymous INSERT on suppliers" ON public.suppliers
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- STEP 4: Create policy to allow 'anon' role to UPDATE suppliers
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow anonymous UPDATE on suppliers" ON public.suppliers;

CREATE POLICY "Allow anonymous UPDATE on suppliers" ON public.suppliers
    FOR UPDATE
    TO anon
    USING (true)
    WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- STEP 5: Create policy to allow 'anon' role to DELETE from suppliers
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow anonymous DELETE on suppliers" ON public.suppliers;

CREATE POLICY "Allow anonymous DELETE on suppliers" ON public.suppliers
    FOR DELETE
    TO anon
    USING (true);

-- -----------------------------------------------------------------------------
-- STEP 6: Grant table permissions to anon role
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.suppliers TO anon;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon;

-- =============================================================================
-- Verification: Check if RLS is enabled and policies exist
-- =============================================================================
SELECT 
    'Table: ' || tablename AS info,
    rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public' 
AND tablename = 'suppliers';

SELECT 
    'Policy: ' || policyname AS info,
    permissive,
    roles::text,
    cmd
FROM pg_policies
WHERE tablename = 'suppliers';

-- =============================================================================
-- If you also need to allow authenticated users, run:
-- =============================================================================
/*
-- For authenticated users:
CREATE POLICY "Allow authenticated SELECT on suppliers" ON public.suppliers
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated INSERT on suppliers" ON public.suppliers
    FOR INSERT TO authenticated WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.suppliers TO authenticated;
*/

