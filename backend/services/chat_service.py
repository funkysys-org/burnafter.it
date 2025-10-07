import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.models.db_client import execute_query

class ChatService:
    """Service for managing ephemeral chat rooms"""

    @staticmethod
    def create_chat_room() -> Dict[str, Any]:
        """Create a new chat room"""
        # Generate alphanumeric hash
        chars = string.ascii_letters + string.digits
        chat_hash = ''.join(secrets.choice(chars) for _ in range(16))

        # Chat rooms expire after 5 minutes
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        query = """
            INSERT INTO chat_rooms (hash, expires_at)
            VALUES (%s, %s)
            RETURNING id, hash, created_at, expires_at
        """

        try:
            result = execute_query(query, (chat_hash, expires_at), fetch_one=True)

            if result:
                return {
                    'success': True,
                    'hash': chat_hash,
                    'chat_room': dict(result)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create chat room'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_chat_room(chat_hash: str) -> Dict[str, Any]:
        """Get chat room details"""
        query = "SELECT * FROM chat_rooms WHERE hash = %s"
        result = execute_query(query, (chat_hash,), fetch_one=True)

        if result:
            result_dict = dict(result)
            # Check if expired
            expires_at = result_dict['expires_at']
            if expires_at > datetime.utcnow():
                return {
                    'success': True,
                    'chat_room': result_dict
                }
            else:
                return {
                    'success': False,
                    'error': 'Chat room expired'
                }
        else:
            return {
                'success': False,
                'error': 'Chat room not found'
            }

    @staticmethod
    def add_message_to_chat(chat_hash: str, shout_id: str) -> Dict[str, Any]:
        """Add a message (shout) to a chat room"""
        # First, get the chat room
        chat_query = "SELECT id FROM chat_rooms WHERE hash = %s"
        chat_result = execute_query(chat_query, (chat_hash,), fetch_one=True)

        if not chat_result:
            return {
                'success': False,
                'error': 'Chat room not found'
            }

        # Add message
        query = """
            INSERT INTO chat_messages (chat_room_id, shout_id)
            VALUES (%s, %s)
            RETURNING id, chat_room_id, shout_id, created_at
        """

        try:
            result = execute_query(query, (chat_result['id'], shout_id), fetch_one=True)

            if result:
                return {
                    'success': True,
                    'message': dict(result)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to add message'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_chat_messages(chat_hash: str) -> List[Dict[str, Any]]:
        """Get all messages in a chat room"""
        # Get chat room
        chat_query = "SELECT id FROM chat_rooms WHERE hash = %s"
        chat_result = execute_query(chat_query, (chat_hash,), fetch_one=True)

        if not chat_result:
            return []

        # Get messages with shout details
        query = """
            SELECT
                cm.id,
                cm.chat_room_id,
                cm.shout_id,
                cm.created_at,
                s.id as shout_id,
                s.hash as shout_hash,
                s.type as shout_type,
                s.content_text as shout_content_text,
                s.storage_key as shout_storage_key,
                s.max_hits as shout_max_hits,
                s.current_hits as shout_current_hits
            FROM chat_messages cm
            JOIN shouts s ON cm.shout_id = s.id
            WHERE cm.chat_room_id = %s
            ORDER BY cm.created_at ASC
        """

        results = execute_query(query, (chat_result['id'],), fetch_all=True)

        if results:
            # Restructure results to match expected format
            messages = []
            for row in results:
                row_dict = dict(row)
                messages.append({
                    'id': row_dict['id'],
                    'chat_room_id': row_dict['chat_room_id'],
                    'shout_id': row_dict['shout_id'],
                    'created_at': row_dict['created_at'].isoformat() if row_dict['created_at'] else None,
                    'shouts': {
                        'type': row_dict['shout_type'],
                        'content_text': row_dict['shout_content_text'],
                        'storage_key': row_dict['shout_storage_key'],
                        'max_hits': row_dict['shout_max_hits'],
                        'current_hits': row_dict['shout_current_hits']
                    }
                })
            return messages

        return []
