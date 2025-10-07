# Changelog

## v2.0.0 - Complete Modernization (Current)

### Major Changes

#### Architecture
- **Full-Stack Separation**: Split monolithic Flask app into backend API + React frontend
- **Modular Backend**: Organized into api/services/models layers
- **RESTful API**: JSON API with proper HTTP methods
- **Docker Support**: Complete containerization with docker-compose

#### Database
- **Migrated from InfluxDB to PostgreSQL** (via Supabase)
- Created proper relational schema (shouts, chat_rooms, chat_messages, hit_logs)
- Implemented Row Level Security (RLS)
- Added database functions for hit tracking and cleanup
- Automatic expiration handling

#### Storage
- **Configurable S3-Compatible Storage** (was: no storage, then Supabase Storage consideration)
- Support for: Minio, AWS S3, DigitalOcean Spaces, Backblaze B2, any S3-compatible
- Included Minio in docker-compose for easy local development
- Presigned URLs for secure media access
- Automatic cleanup of expired files

#### Frontend
- **Complete Rewrite**: React + Vite (was: Flask templates)
- Modern UI with beautiful gradients and animations
- Responsive design for mobile and desktop
- Real-time chat with polling
- QR code generation integrated
- Pages: Home, CreateShout, ViewShout, ChatRoom

#### Backend
- **Modular Structure**:
  - `/api/` - Route handlers
  - `/services/` - Business logic
  - `/models/` - Data access
  - `config.py` - Configuration management
- **Features**:
  - Input validation
  - Error handling
  - CORS support
  - boto3 for S3 operations
  - Automated cleanup service

#### Security
- Input validation and sanitization
- XSS prevention
- CORS configuration
- Row Level Security in database
- Presigned URLs (5-minute expiry)
- Secure file handling

#### Deployment
- Docker Compose orchestration
- Health checks for all services
- Easy startup scripts
- Production-ready configuration

### New Features

1. **Storage Flexibility**
   - Choose any S3-compatible provider
   - Self-host with Minio
   - Or use AWS S3, DigitalOcean Spaces, etc.

2. **Modern UI**
   - Animated icons
   - Gradient backgrounds
   - Mobile responsive
   - Smooth transitions

3. **Improved Chat**
   - Cleaner interface
   - Better message display
   - Easier sharing (QR codes)

4. **Automated Cleanup**
   - Database cleanup function
   - Storage cleanup service
   - Admin endpoint for manual trigger

5. **Better Developer Experience**
   - Clear code structure
   - Comprehensive documentation
   - Easy local development
   - Hot reload in dev mode

### Breaking Changes

1. **API Endpoints Changed**
   - Old: `/post/text`, `/stream_any/{type}/{hash}`
   - New: `/api/shouts/create`, `/api/shouts/{hash}`

2. **Database**
   - Complete schema change
   - No migration path from v1 (different database system)

3. **Storage**
   - Different storage mechanism
   - Must configure S3-compatible storage

4. **User Accounts**
   - Removed (was disabled in v1 anyway)
   - Fully anonymous now

5. **Configuration**
   - Different environment variables
   - See `.env.example` for new format

### Removed Features

- User registration/login (was disabled)
- Redis sessions (stateless now)
- InfluxDB integration
- Direct Minio configuration in config.json

### Dependencies

#### Backend
- Added: boto3 (S3 operations)
- Updated: Flask 3.0, supabase 2.3.0
- Kept: qrcode, Pillow

#### Frontend
- New: React 18, Vite 5, React Router 6, Axios
- All new modern dependencies

### Documentation

New documentation files:
- `README.md` - Updated main documentation
- `QUICK_START.md` - 5-minute setup guide
- `STORAGE_SETUP.md` - Complete storage configuration guide
- `STORAGE_QUICK_SETUP.md` - Quick storage setup
- `STORAGE_CHANGES.md` - Storage implementation details
- `PROJECT_SUMMARY.md` - Architecture overview
- `MIGRATION_GUIDE.md` - v1 to v2 migration
- `FILE_STRUCTURE.txt` - Complete file structure
- `CHANGELOG.md` - This file

### File Structure

```
New structure:
backend/
  api/          - Route handlers
  services/     - Business logic
  models/       - Data access
  config.py     - Configuration

frontend/
  src/
    api/        - API client
    pages/      - Page components
    App.jsx     - Main app

docker-compose.yml - Orchestration
```

### Performance

- Faster page loads (React SPA)
- Better caching (client-side state)
- Optimized builds (Vite)
- CDN-ready (static files)

### Cost

- Reduced infrastructure costs
- Supabase free tier available
- Minio self-hosted option
- Or cheap cloud storage ($5-20/month)

### Testing

To test the new version:

1. Set up Supabase database
2. Configure S3 storage (Minio included)
3. Start with `./start-docker.sh`
4. Access at http://localhost:3000

### Known Issues

- Chat uses polling instead of WebSockets
- No automatic tests yet
- Cleanup must be triggered manually

### Future Enhancements

Planned for future releases:
- WebSocket for real-time chat
- Automated tests
- CI/CD pipeline
- Rate limiting
- Content moderation
- User authentication (optional)

---

## v1.0.0 - Original Version

- Monolithic Flask application
- InfluxDB for data storage
- Minio for file storage
- Redis for sessions
- Server-rendered templates
- User accounts (disabled)
- Manual deployment

