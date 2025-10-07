-- Run this SQL in your Supabase SQL Editor to set up storage policies
-- Or execute manually through the Supabase dashboard

-- Create the storage bucket (if it doesn't exist)
INSERT INTO storage.buckets (id, name, public)
VALUES ('shouts', 'shouts', true)
ON CONFLICT (id) DO NOTHING;

-- Policy 1: Allow public read access for signed URLs
CREATE POLICY IF NOT EXISTS "Public can read shouts"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'shouts');

-- Policy 2: Allow anyone to upload (for anonymous shouts)
CREATE POLICY IF NOT EXISTS "Anyone can upload shouts"
ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'shouts');

-- Policy 3: Allow service role to delete (for cleanup)
CREATE POLICY IF NOT EXISTS "Service can delete shouts"
ON storage.objects FOR DELETE
TO public
USING (bucket_id = 'shouts');

-- Policy 4: Allow updates (for file replacements if needed)
CREATE POLICY IF NOT EXISTS "Service can update shouts"
ON storage.objects FOR UPDATE
TO public
USING (bucket_id = 'shouts')
WITH CHECK (bucket_id = 'shouts');

-- Verify the bucket was created
SELECT * FROM storage.buckets WHERE id = 'shouts';

-- View the policies
SELECT * FROM pg_policies WHERE tablename = 'objects' AND schemaname = 'storage';
