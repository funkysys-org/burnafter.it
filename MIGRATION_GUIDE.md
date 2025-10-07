# Migration Guide: BurnAfterIt v1 to v2

This guide helps you migrate from the original BurnAfterIt to the modernized v2.0.

## Key Changes

### Architecture
- **Monolithic → Microservices**: Separated into backend API and frontend SPA
- **InfluxDB → PostgreSQL**: Using Supabase for relational database
- **Minio → Supabase Storage**: Integrated storage solution
- **Redis → Session-less**: Stateless API with client-side state management

### Technology Stack

| Component | v1 | v2 |
|-----------|----|----|
| Frontend | Flask Templates | React + Vite |
| Backend | Flask Monolith | Flask REST API |
| Database | InfluxDB | PostgreSQL (Supabase) |
| Storage | Minio | Supabase Storage |
| Sessions | Redis | Stateless |
| Deployment | Manual | Docker Compose |

## Migration Steps

### 1. Export Existing Data (Optional)

If you want to preserve existing shouts:

```python
# Export from InfluxDB
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

# Query all shouts
shouts = query_api.query('''
    from(bucket:"burnafterit")
    |> range(start: -30d)
    |> filter(fn: (r) => r["_measurement"] == "shout")
''')

# Save to JSON for manual import
import json
with open('shouts_export.json', 'w') as f:
    json.dump([record.values for record in shouts[0].records], f)
```

### 2. Set Up Supabase

1. Create a Supabase project at https://supabase.com
2. Note your project URL and anon key
3. Run the migration from `supabase/migrations/`
4. Create the storage bucket as per `setup_supabase_storage.md`

### 3. Update Environment Variables

Old `.env`:
```
INFLUX_ENDPOINT_URL=...
INFLUX_TOKEN=...
INFLUX_ORG=...
INFLUX_BUCKET=...
S3_ENDPOINT_URL=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
REDIS_HOST=...
```

New `.env`:
```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
VITE_API_URL=http://localhost:5000
VITE_APP_URL=http://localhost:3000
```

### 4. Migrate Media Files (If Needed)

If you want to preserve media files:

```python
import boto3
from supabase import create_client

# Old Minio client
old_s3 = boto3.client('s3', endpoint_url=OLD_ENDPOINT, ...)

# New Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# List and migrate files
objects = old_s3.list_objects(Bucket='burnafterit')
for obj in objects.get('Contents', []):
    # Download from Minio
    file_data = old_s3.get_object(Bucket='burnafterit', Key=obj['Key'])

    # Upload to Supabase
    supabase.storage.from_('shouts').upload(
        obj['Key'],
        file_data['Body'].read()
    )
```

### 5. Deploy New Version

Using Docker:
```bash
docker-compose up -d --build
```

Or development mode:
```bash
./start-dev.sh
```

## API Changes

### Creating a Shout

**Old (v1)**:
```python
# POST /post/text
data = {
    'data': 'message',
    'to': 'recipient',
    'maxhits': 1,
    'maxtime': 240
}
```

**New (v2)**:
```javascript
// POST /api/shouts/create
{
    "type": "text",
    "maxhits": 1,
    "maxtime": 240,
    "data": "message"
}
```

### Viewing a Shout

**Old (v1)**:
```
GET /stream_any/text/{hash}?valid=1
```

**New (v2)**:
```
GET /api/shouts/{hash}
```

### Chat Rooms

**Old (v1)**:
```
GET /chat  # Creates random hash
GET /chat/{hash}  # View chat
```

**New (v2)**:
```
POST /api/chat/create  # Returns hash
GET /api/chat/{hash}  # Get chat details
GET /api/chat/{hash}/messages  # Get messages
```

## Feature Comparison

| Feature | v1 | v2 |
|---------|----|----|
| Text shouts | ✅ | ✅ |
| Audio shouts | ✅ | ✅ |
| Video shouts | ✅ | ✅ |
| Photo shouts | ✅ | ✅ |
| Ephemeral chat | ✅ | ✅ |
| QR codes | ✅ | ✅ |
| User accounts | ⚠️ (disabled) | ❌ (removed) |
| Max hits control | ✅ | ✅ |
| Time expiration | ✅ | ✅ |
| View tracking | ✅ | ✅ (improved) |
| Auto-cleanup | ❌ | ✅ |
| Mobile responsive | ⚠️ | ✅ |
| Modern UI | ❌ | ✅ |
| Docker support | ❌ | ✅ |
| API-first | ❌ | ✅ |

## Breaking Changes

1. **No user accounts**: The v2 removes user authentication (it was disabled in v1 anyway)
2. **Different URLs**: API endpoints have changed
3. **No Redis sessions**: Application is now stateless
4. **Database schema**: Complete rewrite, no direct migration path
5. **Storage structure**: Files are stored differently in Supabase

## Benefits of v2

1. **Modern Architecture**: Clean separation of frontend and backend
2. **Better Performance**: React SPA with API caching
3. **Easier Deployment**: Docker Compose for one-command deployment
4. **Better Security**: RLS policies, input validation, CORS protection
5. **Maintainability**: Modular code structure
6. **Scalability**: Stateless API, managed database
7. **Cost Effective**: Supabase free tier vs self-hosted InfluxDB + Minio + Redis

## Rollback Plan

If you need to rollback:

1. Keep v1 running during migration
2. Use different domains/ports for v2
3. Switch DNS/reverse proxy when ready
4. Keep v1 data for 30 days

## Support

For issues during migration:
1. Check logs: `docker-compose logs -f`
2. Verify Supabase setup
3. Check environment variables
4. Review the README.new.md

## Timeline Recommendation

- **Day 1**: Set up Supabase, test with sample data
- **Day 2-3**: Deploy v2 in parallel, test all features
- **Day 4**: Migrate data if needed
- **Day 5**: Switch traffic to v2
- **Day 6-30**: Monitor and keep v1 as backup
