from flask import Blueprint, request, jsonify
from backend.services.chat_service import ChatService
from backend.services.shout_service import ShoutService
from backend.services.validation import ValidationService
import base64

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

@chat_bp.route('/create', methods=['POST'])
def create_chat_room():
    """Create a new chat room"""
    try:
        result = ChatService.create_chat_room()

        if result['success']:
            return jsonify({
                'success': True,
                'hash': result['hash'],
                'chat_room': result['chat_room']
            }), 201
        else:
            return jsonify({'error': result['error']}), 500

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@chat_bp.route('/<chat_hash>', methods=['GET'])
def get_chat_room(chat_hash):
    """Get chat room details"""
    try:
        result = ChatService.get_chat_room(chat_hash)

        if result['success']:
            return jsonify({
                'success': True,
                'chat_room': result['chat_room']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@chat_bp.route('/<chat_hash>/messages', methods=['GET'])
def get_chat_messages(chat_hash):
    """Get all messages in a chat room"""
    try:
        messages = ChatService.get_chat_messages(chat_hash)

        # Add media URLs to messages
        for message in messages:
            if message.get('shouts') and message['shouts'].get('storage_key'):
                media_url = ShoutService.get_media_url(message['shouts']['storage_key'])
                message['shouts']['media_url'] = media_url

        return jsonify({
            'success': True,
            'messages': messages
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@chat_bp.route('/<chat_hash>/message', methods=['POST'])
def post_chat_message(chat_hash):
    """Post a new message to a chat room"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Validate chat room exists
        chat_result = ChatService.get_chat_room(chat_hash)
        if not chat_result['success']:
            return jsonify({'error': 'Chat room not found or expired'}), 404

        # Get message type
        message_type = data.get('type', 'audio')
        max_hits = int(data.get('maxhits', 10))  # Chat messages can be viewed more
        max_time = int(data.get('maxtime', 5))    # But expire quickly

        # Validate type
        type_validation = ValidationService.validate_shout_type(message_type)
        if not type_validation['valid']:
            return jsonify({'error': type_validation['error']}), 400

        storage_key = None
        content_text = None

        # Handle text message
        if message_type == 'text':
            text = data.get('data', '')
            text_validation = ValidationService.validate_text_content(text)
            if not text_validation['valid']:
                return jsonify({'error': text_validation['error']}), 400
            content_text = ValidationService.sanitize_text(text_validation['value'])

        # Handle media
        else:
            if 'data' in request.files:
                file = request.files['data']
                file_data = file.read()
            elif 'data' in data and isinstance(data['data'], str):
                try:
                    if 'data:image/' in data['data']:
                        base64_str = data['data'].split(',')[1] if ',' in data['data'] else data['data']
                        file_data = base64.b64decode(base64_str)
                    else:
                        return jsonify({'error': 'Invalid data format'}), 400
                except Exception as e:
                    return jsonify({'error': f'Failed to decode data: {str(e)}'}), 400
            else:
                return jsonify({'error': 'No file data provided'}), 400

            # Validate and upload
            size_validation = ValidationService.validate_file_size(len(file_data), message_type)
            if not size_validation['valid']:
                return jsonify({'error': size_validation['error']}), 400

            import secrets
            temp_hash = secrets.token_urlsafe(36)
            file_ext = ValidationService.get_file_extension(message_type)

            upload_result = ShoutService.upload_media(file_data, temp_hash, file_ext)
            if not upload_result['success']:
                return jsonify({'error': upload_result['error']}), 500

            storage_key = upload_result['storage_key']

        # Create shout for the message
        shout_result = ShoutService.create_shout(
            shout_type=message_type,
            max_hits=max_hits,
            max_time_minutes=max_time,
            content_text=content_text,
            storage_key=storage_key
        )

        if not shout_result['success']:
            return jsonify({'error': 'Failed to create message'}), 500

        # Get shout ID
        from backend.models.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        shout_data = supabase.table('shouts').select('id').eq('hash', shout_result['hash']).single().execute()

        if not shout_data.data:
            return jsonify({'error': 'Failed to retrieve message'}), 500

        # Add message to chat
        message_result = ChatService.add_message_to_chat(chat_hash, shout_data.data['id'])

        if message_result['success']:
            return jsonify({
                'success': True,
                'message': message_result['message'],
                'shout_hash': shout_result['hash']
            }), 201
        else:
            return jsonify({'error': message_result['error']}), 500

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
