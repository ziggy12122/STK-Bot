
import os
from typing import Optional

class BotConfig:
    """Centralized configuration for the Discord shop bot"""
    
    # Bot settings
    PREFIX = '!'
    
    # Discord IDs (set via environment variables)
    ADMIN_ROLE_ID: Optional[int] = None
    SHOP_CHANNEL_ID: Optional[int] = None
    TICKET_CHANNEL_ID: Optional[int] = None
    CUSTOMER_ROLE_ID: Optional[int] = None
    
    # Database settings
    DATABASE_PATH = 'shop.db'
    
    # Embed colors (hex)
    COLORS = {
        'success': 0x2ecc71,
        'error': 0xe74c3c,
        'info': 0x3498db,
        'warning': 0xf39c12,
        'shop': 0x4ecdc4,
        'admin': 0x9b59b6
    }
    
    # Shop settings
    ITEMS_PER_PAGE = 1  # Products shown per page in shop browser
    CART_TIMEOUT = 3600  # Cart session timeout in seconds
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        cls.ADMIN_ROLE_ID = cls._get_int_env('ADMIN_ROLE_ID')
        cls.SHOP_CHANNEL_ID = cls._get_int_env('SHOP_CHANNEL_ID')
        cls.TICKET_CHANNEL_ID = cls._get_int_env('TICKET_CHANNEL_ID')
        cls.CUSTOMER_ROLE_ID = cls._get_int_env('CUSTOMER_ROLE_ID')
    
    @staticmethod
    def _get_int_env(key: str) -> Optional[int]:
        """Safely convert environment variable to integer"""
        try:
            value = os.getenv(key)
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_bot_token(cls) -> str:
        """Get Discord bot token from environment"""
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable not set!")
        return token

# Load configuration on import
BotConfig.load_from_env()
