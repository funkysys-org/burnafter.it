import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.models.supabase_client import get_supabase_client

class ShoutService:
    """Service for managing shouts (ephemeral content)"""

    @staticmethod
    def create_shout(
        shout_type: str,
        max_hits: int,
        max_time_minutes: int,
        content_text: Optional[str] = None,
        storage_key: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new shout"""
        supabase = get_supabase_client()

        # Generate unique hash
        shout_hash = secrets.token_urlsafe(36)

        # Calculate expiration time
        expires_at = (datetime.utcnow() + timedelta(minutes=max_time_minutes)).isoformat()

        # Create shout record
        data = {
            'hash': shout_hash,
            'type': shout_type,
            'max_hits': max_hits,
            'max_time_minutes': max_time_minutes,
            'content_text': content_text,
            'storage_key': storage_key,
            'user_id': user_id,
            'expires_at': expires_at
        }

        result = supabase.table('shouts').insert(data).execute()

        if result.data:
            return {
                'success': True,
                'hash': shout_hash,
                'shout': result.data[0]
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create shout'
            }

    @staticmethod
    def get_shout(shout_hash: str, client_ip: str, user_agent: str) -> Dict[str, Any]:
        """Get a shout and increment hit count"""
        supabase = get_supabase_client()

        try:
            # Call the database function to increment hit and validate
            result = supabase.rpc(
                'increment_shout_hit',
                {
                    'shout_hash': shout_hash,
                    'client_ip': client_ip,
                    'client_ua': user_agent
                }
            ).execute()

            if result.data:
                return result.data
            else:
                return {'valid': False, 'reason': 'not_found'}

        except Exception as e:
            return {'valid': False, 'reason': 'error', 'message': str(e)}

    @staticmethod
    def check_shout_exists(shout_hash: str) -> bool:
        """Check if a shout exists without incrementing hit count"""
        supabase = get_supabase_client()

        result = supabase.table('shouts').select('id').eq('hash', shout_hash).maybeSingle().execute()

        return result.data is not None

    @staticmethod
    def upload_media(file_data: bytes, shout_hash: str, file_extension: str) -> Dict[str, Any]:
        """Upload media file to Supabase Storage"""
        supabase = get_supabase_client()

        try:
            # Create storage key
            storage_key = f"{shout_hash}{file_extension}"

            # Upload to Supabase Storage
            result = supabase.storage.from_('shouts').upload(
                storage_key,
                file_data,
                file_options={'content-type': f'application/octet-stream'}
            )

            if result:
                return {
                    'success': True,
                    'storage_key': storage_key
                }
            else:
                return {
                    'success': False,
                    'error': 'Upload failed'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_media_url(storage_key: str, expires_in: int = 300) -> Optional[str]:
        """Get signed URL for media file"""
        supabase = get_supabase_client()

        try:
            result = supabase.storage.from_('shouts').create_signed_url(
                storage_key,
                expires_in
            )

            return result.get('signedURL') if result else None

        except Exception as e:
            print(f"Error getting media URL: {e}")
            return None
