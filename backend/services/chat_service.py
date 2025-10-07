import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.models.supabase_client import get_supabase_client

class ChatService:
    """Service for managing ephemeral chat rooms"""

    @staticmethod
    def create_chat_room() -> Dict[str, Any]:
        """Create a new chat room"""
        supabase = get_supabase_client()

        # Generate alphanumeric hash (like original)
        chars = string.ascii_letters + string.digits
        chat_hash = ''.join(secrets.choice(chars) for _ in range(16))

        # Chat rooms expire after 5 minutes
        expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

        data = {
            'hash': chat_hash,
            'expires_at': expires_at
        }

        result = supabase.table('chat_rooms').insert(data).execute()

        if result.data:
            return {
                'success': True,
                'hash': chat_hash,
                'chat_room': result.data[0]
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create chat room'
            }

    @staticmethod
    def get_chat_room(chat_hash: str) -> Dict[str, Any]:
        """Get chat room details"""
        supabase = get_supabase_client()

        result = supabase.table('chat_rooms').select('*').eq('hash', chat_hash).maybeSingle().execute()

        if result.data:
            # Check if expired
            expires_at = datetime.fromisoformat(result.data['expires_at'].replace('Z', '+00:00'))
            if expires_at > datetime.utcnow():
                return {
                    'success': True,
                    'chat_room': result.data
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
        supabase = get_supabase_client()

        # First, get the chat room
        chat_result = supabase.table('chat_rooms').select('id').eq('hash', chat_hash).maybeSingle().execute()

        if not chat_result.data:
            return {
                'success': False,
                'error': 'Chat room not found'
            }

        # Add message
        data = {
            'chat_room_id': chat_result.data['id'],
            'shout_id': shout_id
        }

        result = supabase.table('chat_messages').insert(data).execute()

        if result.data:
            return {
                'success': True,
                'message': result.data[0]
            }
        else:
            return {
                'success': False,
                'error': 'Failed to add message'
            }

    @staticmethod
    def get_chat_messages(chat_hash: str) -> List[Dict[str, Any]]:
        """Get all messages in a chat room"""
        supabase = get_supabase_client()

        # Get chat room
        chat_result = supabase.table('chat_rooms').select('id').eq('hash', chat_hash).maybeSingle().execute()

        if not chat_result.data:
            return []

        # Get messages with shout details
        result = supabase.table('chat_messages')\
            .select('*, shouts(*)')\
            .eq('chat_room_id', chat_result.data['id'])\
            .order('created_at', desc=False)\
            .execute()

        return result.data if result.data else []
