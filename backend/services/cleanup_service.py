from backend.models.db_client import execute_query
from backend.services.shout_service import ShoutService
import logging

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for cleaning up expired content"""

    @staticmethod
    def cleanup_expired_content():
        """Run cleanup for expired shouts and chat rooms"""
        try:
            # Call the database cleanup function
            query = "SELECT cleanup_expired_content()"
            execute_query(query)

            logger.info("Cleanup completed successfully")
            return {'success': True}

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_expired_storage_files():
        """Delete storage files for expired shouts from S3"""
        try:
            # Get inactive shouts with storage keys
            query = """
                SELECT storage_key
                FROM shouts
                WHERE is_active = false
                AND storage_key IS NOT NULL
            """
            results = execute_query(query, fetch_all=True)

            deleted_count = 0

            if results:
                for row in results:
                    try:
                        # Delete from S3 storage
                        if ShoutService.delete_media(row['storage_key']):
                            deleted_count += 1
                            logger.info(f"Deleted storage file: {row['storage_key']}")
                    except Exception as e:
                        logger.error(f"Failed to delete {row['storage_key']}: {str(e)}")

                # Mark as cleaned (remove storage_key reference)
                storage_keys = [row['storage_key'] for row in results]
                if storage_keys:
                    placeholders = ','.join(['%s'] * len(storage_keys))
                    update_query = f"""
                        UPDATE shouts
                        SET storage_key = NULL
                        WHERE storage_key IN ({placeholders})
                    """
                    execute_query(update_query, tuple(storage_keys))

            return {'success': True, 'deleted': deleted_count}

        except Exception as e:
            logger.error(f"Storage cleanup failed: {str(e)}")
            return {'success': False, 'error': str(e)}
