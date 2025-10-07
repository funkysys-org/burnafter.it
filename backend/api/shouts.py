from flask import Blueprint, request, jsonify
from backend.services.shout_service import ShoutService
from backend.services.validation import ValidationService
import base64

shouts_bp = Blueprint('shouts', __name__, url_prefix='/api/shouts')

@shouts_bp.route('/create', methods=['POST'])
def create_shout():
    """Create a new shout"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Validate required fields
        shout_type = data.get('type')
        max_hits = data.get('maxhits', 1)
        max_time = data.get('maxtime', 240)

        # Validate type
        type_validation = ValidationService.validate_shout_type(shout_type)
        if not type_validation['valid']:
            return jsonify({'error': type_validation['error']}), 400

        # Validate max_hits
        hits_validation = ValidationService.validate_max_hits(max_hits)
        if not hits_validation['valid']:
            return jsonify({'error': hits_validation['error']}), 400
        max_hits = hits_validation['value']

        # Validate max_time
        time_validation = ValidationService.validate_max_time(max_time)
        if not time_validation['valid']:
            return jsonify({'error': time_validation['error']}), 400
        max_time = time_validation['value']

        storage_key = None
        content_text = None

        # Handle text content
        if shout_type == 'text':
            text = data.get('data', '')
            text_validation = ValidationService.validate_text_content(text)
            if not text_validation['valid']:
                return jsonify({'error': text_validation['error']}), 400

            content_text = ValidationService.sanitize_text(text_validation['value'])

        # Handle media upload
        else:
            # Check if file is in request
            if 'data' in request.files:
                file = request.files['data']
                file_data = file.read()
            elif 'data' in data and isinstance(data['data'], str):
                # Handle base64 encoded data (for photos from canvas)
                try:
                    if 'data:image/' in data['data']:
                        # Remove data URI prefix
                        base64_str = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                        file_data = base64.b64decode(base64_str)
                    else:
                        return jsonify({'error': 'Invalid data format'}), 400
                except Exception as e:
                    return jsonify({'error': f'Failed to decode data: {str(e)}'}), 400
            else:
                return jsonify({'error': 'No file data provided'}), 400

            # Validate file size
            size_validation = ValidationService.validate_file_size(len(file_data), shout_type)
            if not size_validation['valid']:
                return jsonify({'error': size_validation['error']}), 400

            # Generate temporary hash for upload
            import secrets
            temp_hash = secrets.token_urlsafe(36)
            file_ext = ValidationService.get_file_extension(shout_type)

            # Upload to storage
            upload_result = ShoutService.upload_media(file_data, temp_hash, file_ext)
            if not upload_result['success']:
                return jsonify({'error': upload_result['error']}), 500

            storage_key = upload_result['storage_key']

        # Create shout
        result = ShoutService.create_shout(
            shout_type=shout_type,
            max_hits=max_hits,
            max_time_minutes=max_time,
            content_text=content_text,
            storage_key=storage_key
        )

        if result['success']:
            return jsonify({
                'success': True,
                'hash': result['hash'],
                'url': f"/stream/{shout_type}/{result['hash']}"
            }), 201
        else:
            return jsonify({'error': result['error']}), 500

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@shouts_bp.route('/<shout_hash>', methods=['GET'])
def get_shout(shout_hash):
    """Get a shout (increments view count)"""
    try:
        # Get client info
        user_agent = request.headers.get('User-Agent', 'Unknown')
        client_ip = request.remote_addr or 'Unknown'

        # Check for preview mode (don't increment)
        preview = request.args.get('preview', '0') == '1'

        if preview:
            # Just check if exists
            exists = ShoutService.check_shout_exists(shout_hash)
            if exists:
                return jsonify({
                    'valid': True,
                    'preview': True
                }), 200
            else:
                return jsonify({
                    'valid': False,
                    'reason': 'not_found'
                }), 404

        # Get and increment
        result = ShoutService.get_shout(shout_hash, client_ip, user_agent)

        if result.get('valid'):
            shout = result['shout']

            # Get media URL if needed
            if shout.get('storage_key'):
                media_url = ShoutService.get_media_url(shout['storage_key'])
                shout['media_url'] = media_url

            return jsonify({
                'valid': True,
                'shout': shout
            }), 200
        else:
            return jsonify({
                'valid': False,
                'reason': result.get('reason', 'unknown')
            }), 404

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@shouts_bp.route('/check/<shout_hash>', methods=['GET'])
def check_shout(shout_hash):
    """Check if a shout exists without incrementing view count"""
    try:
        exists = ShoutService.check_shout_exists(shout_hash)
        return jsonify({'exists': exists}), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
