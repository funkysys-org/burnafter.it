# Quick Storage Setup

Choose one of these options to get started quickly.

## Option 1: Minio (Docker - Easiest)

1. Edit `docker-compose.yml` - remove line 26: `profiles: ["minio"]`

2. Edit `.env`:
```bash
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_USE_SSL=False
```

3. Start:
```bash
docker-compose up -d
```

4. Create bucket:
   - Open http://localhost:9001
   - Login: `minioadmin` / `minioadmin`
   - Create bucket named `burnafterit`
   - Set to Public

## Option 2: AWS S3

1. Create S3 bucket in AWS Console
2. Create IAM user with S3 access
3. Update `.env`:
```bash
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=your_aws_key
S3_SECRET_KEY=your_aws_secret
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
S3_USE_SSL=True
```

## Option 3: DigitalOcean Spaces

1. Create Space in DO dashboard
2. Generate Spaces Keys
3. Update `.env`:
```bash
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_ACCESS_KEY=your_do_key
S3_SECRET_KEY=your_do_secret
S3_BUCKET=your-space-name
S3_REGION=us-east-1
S3_USE_SSL=True
```

For detailed configuration, see [STORAGE_SETUP.md](STORAGE_SETUP.md)
