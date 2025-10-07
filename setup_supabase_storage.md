# Supabase Storage Setup Instructions

After setting up your Supabase project, you need to create the storage bucket for media files.

## Step 1: Create Storage Bucket

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Navigate to **Storage** in the left sidebar
4. Click **New bucket**
5. Configure the bucket:
   - **Name**: `shouts`
   - **Public bucket**: ✓ Enabled (so we can generate signed URLs)
   - Click **Create bucket**

## Step 2: Configure Storage Policies

The bucket needs to allow:
- Public read access for signed URLs
- Authenticated uploads

### Policy 1: Allow Public Read (for signed URLs)
```sql
CREATE POLICY "Public can read shouts"
ON storage.objects FOR SELECT
USING (bucket_id = 'shouts');
```

### Policy 2: Allow Public Uploads (for anonymous shouts)
```sql
CREATE POLICY "Anyone can upload shouts"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'shouts');
```

### Policy 3: Allow Deletions (for cleanup)
```sql
CREATE POLICY "Service can delete shouts"
ON storage.objects FOR DELETE
USING (bucket_id = 'shouts');
```

## Step 3: Verify Setup

Test the setup by:
1. Starting the application
2. Creating a shout with a photo/audio/video
3. Viewing the shout to ensure media loads correctly

## Alternative: Use Supabase CLI

If you have Supabase CLI installed:

```bash
# Create bucket
supabase storage create shouts --public

# Or via SQL
supabase db execute "
CREATE POLICY 'Public can read shouts'
ON storage.objects FOR SELECT
USING (bucket_id = 'shouts');

CREATE POLICY 'Anyone can upload shouts'
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'shouts');

CREATE POLICY 'Service can delete shouts'
ON storage.objects FOR DELETE
USING (bucket_id = 'shouts');
"
```

## Note on Security

The bucket is set to public to allow signed URL generation. Individual files are protected by:
1. Obscure/random filenames (36-character tokens)
2. Short-lived signed URLs (5 minutes)
3. Application-level access control (view count limits)
4. Automatic expiration and cleanup

The combination of these measures ensures content security while allowing necessary access.
