# Storage Implementation Changes

## Summary

The storage system has been updated to use **configurable S3-compatible storage** instead of being locked to Supabase Storage. This gives administrators full control over their storage provider.

## What Changed

### Before
- **Locked to Supabase Storage**
- No choice of storage provider
- Limited to Supabase's storage features
- Tied to Supabase ecosystem

### After
- **Any S3-compatible storage**
- Choose: Minio, AWS S3, DigitalOcean Spaces, Backblaze B2, Wasabi, etc.
- Full control over storage infrastructure
- Cost optimization possible
- Self-hosted option available

## Technical Changes

### 1. Backend Configuration (`backend/config.py`)

Added S3 configuration options:
```python
S3_ENDPOINT_URL
S3_ACCESS_KEY
S3_SECRET_KEY
S3_BUCKET
S3_REGION
S3_USE_SSL
S3_SIGNATURE_VERSION
```

### 2. Storage Service (`backend/services/shout_service.py`)

- Replaced Supabase Storage client with boto3
- Added `_get_s3_client()` method
- Updated `upload_media()` to use S3 put_object
- Updated `get_media_url()` to generate presigned URLs
- Added `delete_media()` for cleanup

### 3. Cleanup Service (`backend/services/cleanup_service.py`)

- Updated to use S3 delete operations
- Uses ShoutService.delete_media() method

### 4. Dependencies (`backend/requirements.txt`)

- Added `boto3==1.34.0` for S3 operations

### 5. Docker Compose (`docker-compose.yml`)

- Added optional Minio service
- Included S3 environment variables in backend
- Added volume for Minio data persistence
- Made Minio optional via profiles

### 6. Environment Files

Updated `.env.example` and `.env` with S3 configuration:
```bash
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_REGION=us-east-1
S3_USE_SSL=False
S3_SIGNATURE_VERSION=s3v4
```

## Storage Provider Options

### Minio (Included)
- **Type**: Self-hosted S3-compatible
- **Included**: Yes (in docker-compose.yml)
- **Cost**: Server costs only
- **Best for**: Development, self-hosting

### AWS S3
- **Type**: Cloud service
- **Cost**: Pay-per-use (~$0.023/GB/month)
- **Best for**: Production, high reliability

### DigitalOcean Spaces
- **Type**: Cloud service
- **Cost**: $5/month (250GB + 1TB transfer)
- **Best for**: Simple pricing, CDN included

### Backblaze B2
- **Type**: Cloud service
- **Cost**: $0.005/GB/month (cheapest)
- **Best for**: Cost-sensitive projects

### Others
- Wasabi
- Cloudflare R2
- Any S3-compatible storage

## Benefits

### 1. Flexibility
- Choose storage provider based on needs
- Switch providers without code changes
- Use multiple regions

### 2. Cost Control
- Self-host with Minio (no per-GB fees)
- Or use cheapest cloud provider
- Optimize costs per use case

### 3. Performance
- Choose closest region
- Use CDN-enabled storage
- Control caching policies

### 4. Independence
- Not locked to Supabase ecosystem
- Can migrate providers easily
- Keep data sovereignty

### 5. Development
- Easy local development with Minio
- No external dependencies needed
- Fast iteration

## Migration Path

If you were using the old version with Supabase Storage:

1. **New installations**: Follow STORAGE_SETUP.md
2. **Existing data**: No automatic migration (different storage paradigm)
3. **Fresh start**: Recommended approach for new version

## Configuration Examples

### Development (Minio)
```bash
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_USE_SSL=False
```

### Production (AWS S3)
```bash
S3_ENDPOINT_URL=https://s3.us-east-1.amazonaws.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_USE_SSL=True
```

### Production (DigitalOcean)
```bash
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_ACCESS_KEY=DO00EXAMPLE
S3_SECRET_KEY=example_secret_key
S3_USE_SSL=True
```

## Security Notes

1. **Presigned URLs**: Media accessed via temporary presigned URLs (5 min expiry)
2. **Bucket permissions**: Set buckets to allow presigned URL access
3. **Credentials**: Never commit S3 credentials to version control
4. **Encryption**: Use encryption at rest when available
5. **Access control**: Use IAM policies to limit access

## File Organization

Files stored with pattern: `{shout_hash}{extension}`

Examples:
- `abc123def456...xyz.wav` (audio)
- `abc123def456...xyz.mp4` (video)
- `abc123def456...xyz.jpeg` (photo)

## Cleanup

Expired content cleanup:
1. Database marks shout as inactive
2. Cleanup service deletes S3 object
3. Database removes storage_key reference

Run manually:
```bash
curl -X POST http://localhost:5000/api/admin/cleanup
```

Or schedule with cron/Supabase functions.

## Documentation

- **[STORAGE_SETUP.md](STORAGE_SETUP.md)** - Complete configuration guide
- **[STORAGE_QUICK_SETUP.md](STORAGE_QUICK_SETUP.md)** - Quick start
- **[README.md](README.md)** - Main documentation

## Testing

Test storage is working:

1. Start application
2. Create a shout with media (photo/audio/video)
3. View the shout
4. Check storage:
   - **Minio**: http://localhost:9001 → burnafterit bucket
   - **AWS S3**: AWS Console → Your bucket
   - **Other**: Provider's web interface

## Support

Issues? Check:
1. S3_ENDPOINT_URL is correct and accessible
2. S3 credentials are valid
3. Bucket exists
4. Bucket permissions allow presigned URLs
5. Firewall allows connection to S3 endpoint

For provider-specific help, see [STORAGE_SETUP.md](STORAGE_SETUP.md)
