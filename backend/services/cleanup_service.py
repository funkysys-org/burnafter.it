from backend.models.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for cleaning up expired content"""

    @staticmethod
    def cleanup_expired_content():
        """Run cleanup for expired shouts and chat rooms"""
        try:
            supabase = get_supabase_client()

            # Call the database cleanup function
            result = supabase.rpc('cleanup_expired_content').execute()

            logger.info("Cleanup completed successfully")
            return {'success': True}

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_expired_storage_files():
        """Delete storage files for expired shouts"""
        try:
            supabase = get_supabase_client()

            # Get inactive shouts with storage keys
            result = supabase.table('shouts')\
                .select('storage_key')\
                .eq('is_active', False)\
                .not_.is_('storage_key', 'null')\
                .execute()

            if result.data:
                for shout in result.data:
                    try:
                        # Delete from storage
                        supabase.storage.from_('shouts').remove([shout['storage_key']])
                        logger.info(f"Deleted storage file: {shout['storage_key']}")
                    except Exception as e:
                        logger.error(f"Failed to delete {shout['storage_key']}: {str(e)}")

                # Mark as cleaned
                storage_keys = [s['storage_key'] for s in result.data]
                supabase.table('shouts')\
                    .update({'storage_key': None})\
                    .in_('storage_key', storage_keys)\
                    .execute()

            return {'success': True, 'deleted': len(result.data) if result.data else 0}

        except Exception as e:
            logger.error(f"Storage cleanup failed: {str(e)}")
            return {'success': False, 'error': str(e)}
