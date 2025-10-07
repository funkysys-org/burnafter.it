# Storage Configuration Guide

BurnAfterIt uses S3-compatible storage for media files (audio, video, photos). You can use any S3-compatible provider.

## Supported Storage Options

- **Minio** (Self-hosted, included in Docker Compose)
- **AWS S3** (Amazon Web Services)
- **DigitalOcean Spaces**
- **Backblaze B2**
- **Wasabi**
- **Any S3-compatible storage**

## Option 1: Minio (Self-Hosted - Recommended for Development)

### Using Docker Compose

The easiest option! Minio is included in the docker-compose.yml file.

**Enable Minio:**

1. Edit `docker-compose.yml` and remove the `profiles: ["minio"]` line from the minio service
2. Configure `.env`:
```bash
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_USE_SSL=False
```

3. Start services:
```bash
docker-compose up -d
```

4. Create the bucket:
   - Open http://localhost:9001 (Minio Console)
   - Login with `minioadmin` / `minioadmin`
   - Click "Buckets" → "Create Bucket"
   - Name it `burnafterit`
   - Set access policy to "Public"

### Manual Minio Installation

```bash
# Download and run Minio
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /data --console-address ":9001"

# Configure .env
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_USE_SSL=False
```

## Option 2: AWS S3

### Setup

1. Create an AWS account at https://aws.amazon.com
2. Go to S3 Console → Create Bucket
3. Configure:
   - Bucket name: `burnafterit-yourdomain`
   - Region: Choose closest to your users
   - Block all public access: **Uncheck** (for presigned URLs)
   - Bucket Versioning: Disabled
   - Default encryption: Enabled

4. Create IAM user with S3 access:
   - Go to IAM → Users → Add User
   - Attach policy: `AmazonS3FullAccess`
   - Save Access Key ID and Secret Access Key

5. Configure `.env`:
```bash
S3_ENDPOINT_URL=https://s3.amazonaws.com
# Or region-specific: https://s3.us-east-1.amazonaws.com
S3_ACCESS_KEY=your_aws_access_key_id
S3_SECRET_KEY=your_aws_secret_access_key
S3_BUCKET=burnafterit-yourdomain
S3_REGION=us-east-1
S3_USE_SSL=True
S3_SIGNATURE_VERSION=s3v4
```

### AWS S3 CORS Configuration

Add this CORS policy to your bucket:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

## Option 3: DigitalOcean Spaces

### Setup

1. Create DigitalOcean account
2. Go to Spaces → Create Space
3. Configure:
   - Region: Choose closest
   - Name: `burnafterit`
   - Enable CDN (optional but recommended)

4. Create Spaces access keys:
   - API → Spaces Keys → Generate New Key
   - Save Key and Secret

5. Configure `.env`:
```bash
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
# Replace nyc3 with your region
S3_ACCESS_KEY=your_spaces_access_key
S3_SECRET_KEY=your_spaces_secret_key
S3_BUCKET=burnafterit
S3_REGION=us-east-1
S3_USE_SSL=True
S3_SIGNATURE_VERSION=s3v4
```

## Option 4: Backblaze B2

### Setup

1. Create Backblaze account at https://www.backblaze.com/b2
2. Create bucket:
   - Go to Buckets → Create a Bucket
   - Name: `burnafterit`
   - Files in Bucket: Public

3. Create application key:
   - App Keys → Add a New Application Key
   - Allow access to: Your bucket
   - Save keyID and applicationKey

4. Configure `.env`:
```bash
S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
# Replace with your endpoint
S3_ACCESS_KEY=your_keyID
S3_SECRET_KEY=your_applicationKey
S3_BUCKET=burnafterit
S3_REGION=us-west-004
S3_USE_SSL=True
S3_SIGNATURE_VERSION=s3v4
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `S3_ENDPOINT_URL` | S3 endpoint URL | `http://localhost:9000` |
| `S3_ACCESS_KEY` | Access key ID | `minioadmin` |
| `S3_SECRET_KEY` | Secret access key | `minioadmin` |
| `S3_BUCKET` | Bucket name | `burnafterit` |
| `S3_REGION` | Region | `us-east-1` |
| `S3_USE_SSL` | Use HTTPS | `True` or `False` |
| `S3_SIGNATURE_VERSION` | Signature version | `s3v4` |

## Testing Storage Configuration

### 1. Check Backend Starts

```bash
cd backend
source venv/bin/activate
python -m backend.app_api
```

You should see no errors about missing S3 configuration.

### 2. Test Upload

Create a test shout with media through the UI or:

```bash
curl -X POST http://localhost:5000/api/shouts/create \
  -F "type=photo" \
  -F "maxhits=1" \
  -F "maxtime=10" \
  -F "data=@test-image.jpg"
```

### 3. Verify in Storage

**Minio:**
- Open http://localhost:9001
- Check `burnafterit` bucket for uploaded files

**AWS S3:**
- Open S3 Console
- Check your bucket

**Other providers:**
- Use their web interface

## Cost Comparison

### Minio (Self-Hosted)
- **Cost**: Server costs only
- **Pros**: Full control, no per-GB fees
- **Cons**: You manage infrastructure

### AWS S3
- **Storage**: $0.023/GB/month
- **Transfer**: $0.09/GB out
- **Requests**: ~$0.005 per 1,000
- **Pros**: Reliable, scalable, global
- **Cons**: Can get expensive at scale

### DigitalOcean Spaces
- **Cost**: $5/month (includes 250GB storage + 1TB transfer)
- **Pros**: Simple pricing, CDN included
- **Cons**: Less global coverage than AWS

### Backblaze B2
- **Storage**: $0.005/GB/month (cheapest!)
- **Transfer**: First 3x storage is free
- **Pros**: Very affordable
- **Cons**: Slower than others

## Troubleshooting

### Error: "S3 upload failed: Could not connect to endpoint"

**Solution**: Check S3_ENDPOINT_URL is correct and accessible

```bash
# Test connectivity
curl $S3_ENDPOINT_URL
```

### Error: "Access Denied"

**Solution**: Check credentials and bucket permissions

```bash
# Verify credentials in .env
cat .env | grep S3_
```

### Error: "Bucket does not exist"

**Solution**: Create the bucket manually in your storage provider

### Presigned URLs not working

**Solution**:
1. Check bucket is public or allows presigned URLs
2. Verify S3_SIGNATURE_VERSION is `s3v4`
3. For Minio, ensure S3_USE_SSL matches your setup

## Security Best Practices

1. **Never commit credentials**: Keep `.env` in `.gitignore`
2. **Use environment variables**: Don't hardcode keys
3. **Restrict bucket access**: Only allow presigned URLs
4. **Rotate keys regularly**: Change access keys periodically
5. **Enable encryption**: Use encryption at rest if available
6. **Monitor usage**: Set up alerts for unusual activity

## Switching Storage Providers

To switch from one provider to another:

1. **Backup existing data** (if needed)
2. Update `.env` with new credentials
3. Restart backend: `docker-compose restart backend`
4. Test with a new upload
5. Optionally migrate old files (manual process)

## Recommended Setup by Environment

### Development
- **Minio** via Docker Compose
- Easy setup, no external dependencies
- Free

### Staging
- **DigitalOcean Spaces** or **Backblaze B2**
- Affordable
- Similar to production

### Production (Low Traffic)
- **Backblaze B2**
- Cheapest option
- Good for < 100GB

### Production (High Traffic)
- **AWS S3** with CloudFront
- Best performance
- Global CDN

### Production (Self-Hosted)
- **Minio** on your servers
- Full control
- Cost-effective at scale
