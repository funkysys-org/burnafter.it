import secrets
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.models.supabase_client import get_supabase_client
from backend.config import Config
import io

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
    def _get_s3_client():
        """Get configured S3 client (Minio, AWS S3, etc.)"""
        s3_config = BotoConfig(
            signature_version=Config.S3_SIGNATURE_VERSION,
            s3={'addressing_style': 'path'} if 'minio' in Config.S3_ENDPOINT_URL.lower() else {}
        )

        return boto3.client(
            's3',
            endpoint_url=Config.S3_ENDPOINT_URL,
            aws_access_key_id=Config.S3_ACCESS_KEY,
            aws_secret_access_key=Config.S3_SECRET_KEY,
            region_name=Config.S3_REGION,
            config=s3_config,
            use_ssl=Config.S3_USE_SSL
        )

    @staticmethod
    def upload_media(file_data: bytes, shout_hash: str, file_extension: str) -> Dict[str, Any]:
        """Upload media file to S3-compatible storage"""
        try:
            s3_client = ShoutService._get_s3_client()

            # Create storage key
            storage_key = f"{shout_hash}{file_extension}"

            # Upload to S3
            file_obj = io.BytesIO(file_data)
            file_size = len(file_data)

            s3_client.put_object(
                Bucket=Config.S3_BUCKET,
                Key=storage_key,
                Body=file_obj,
                ContentLength=file_size
            )

            return {
                'success': True,
                'storage_key': storage_key
            }

        except ClientError as e:
            return {
                'success': False,
                'error': f'S3 upload failed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload error: {str(e)}'
            }

    @staticmethod
    def get_media_url(storage_key: str, expires_in: int = 300) -> Optional[str]:
        """Get presigned URL for media file from S3"""
        try:
            s3_client = ShoutService._get_s3_client()

            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': Config.S3_BUCKET,
                    'Key': storage_key
                },
                ExpiresIn=expires_in
            )

            return url

        except Exception as e:
            print(f"Error getting media URL: {e}")
            return None

    @staticmethod
    def delete_media(storage_key: str) -> bool:
        """Delete media file from S3"""
        try:
            s3_client = ShoutService._get_s3_client()

            s3_client.delete_object(
                Bucket=Config.S3_BUCKET,
                Key=storage_key
            )

            return True

        except Exception as e:
            print(f"Error deleting media: {e}")
            return False
