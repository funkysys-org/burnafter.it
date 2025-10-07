from typing import Dict, Any, Optional
import re

class ValidationService:
    """Service for input validation and sanitization"""

    ALLOWED_TYPES = ['text', 'audio', 'video', 'photo']

    # File extensions
    ALLOWED_EXTENSIONS = {
        'audio': ['.wav', '.mp3', '.ogg'],
        'video': ['.mp4', '.webm'],
        'photo': ['.jpg', '.jpeg', '.png']
    }

    # Size limits (in bytes)
    MAX_FILE_SIZES = {
        'audio': 50 * 1024 * 1024,  # 50MB
        'video': 100 * 1024 * 1024,  # 100MB
        'photo': 10 * 1024 * 1024,   # 10MB
        'text': 10000  # 10KB characters
    }

    @staticmethod
    def validate_shout_type(shout_type: str) -> Dict[str, Any]:
        """Validate shout type"""
        if not shout_type or shout_type not in ValidationService.ALLOWED_TYPES:
            return {
                'valid': False,
                'error': f"Invalid type. Must be one of: {', '.join(ValidationService.ALLOWED_TYPES)}"
            }
        return {'valid': True}

    @staticmethod
    def validate_max_hits(max_hits: int) -> Dict[str, Any]:
        """Validate max hits parameter"""
        try:
            hits = int(max_hits)
            if hits < 1 or hits > 100:
                return {
                    'valid': False,
                    'error': 'Max hits must be between 1 and 100'
                }
            return {'valid': True, 'value': hits}
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'Max hits must be a valid integer'
            }

    @staticmethod
    def validate_max_time(max_time: int) -> Dict[str, Any]:
        """Validate max time parameter"""
        try:
            time = int(max_time)
            if time < 1 or time > 1440:  # Max 24 hours
                return {
                    'valid': False,
                    'error': 'Max time must be between 1 and 1440 minutes'
                }
            return {'valid': True, 'value': time}
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': 'Max time must be a valid integer'
            }

    @staticmethod
    def validate_text_content(text: str) -> Dict[str, Any]:
        """Validate text content"""
        if not text or len(text.strip()) == 0:
            return {
                'valid': False,
                'error': 'Text content cannot be empty'
            }

        if len(text) > ValidationService.MAX_FILE_SIZES['text']:
            return {
                'valid': False,
                'error': f"Text content too long (max {ValidationService.MAX_FILE_SIZES['text']} characters)"
            }

        return {'valid': True, 'value': text.strip()}

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text content (basic XSS prevention)"""
        # Remove potential script tags and dangerous content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def validate_file_size(file_size: int, content_type: str) -> Dict[str, Any]:
        """Validate file size"""
        max_size = ValidationService.MAX_FILE_SIZES.get(content_type, 0)

        if file_size > max_size:
            return {
                'valid': False,
                'error': f"File too large (max {max_size // (1024 * 1024)}MB for {content_type})"
            }

        return {'valid': True}

    @staticmethod
    def get_file_extension(content_type: str, filename: Optional[str] = None) -> str:
        """Get appropriate file extension based on content type"""
        if content_type == 'audio':
            return '.wav'
        elif content_type == 'video':
            return '.mp4'
        elif content_type == 'photo':
            return '.jpeg'
        else:
            return '.bin'
