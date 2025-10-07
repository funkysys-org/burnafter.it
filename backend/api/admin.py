from flask import Blueprint, jsonify
from backend.services.cleanup_service import CleanupService

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/cleanup', methods=['POST'])
def run_cleanup():
    """Manually trigger cleanup (in production, use cron or scheduled job)"""
    try:
        # Run database cleanup
        db_result = CleanupService.cleanup_expired_content()

        # Run storage cleanup
        storage_result = CleanupService.delete_expired_storage_files()

        return jsonify({
            'success': True,
            'database_cleanup': db_result,
            'storage_cleanup': storage_result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
