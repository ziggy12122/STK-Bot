
import os
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file if it exists"""
    if os.path.exists('.env'):
        load_dotenv('.env')
        print("✅ Loaded environment variables from .env file")
    else:
        print("ℹ️  No .env file found, using system environment variables")

def get_required_env(key: str) -> str:
    """Get a required environment variable or raise an error"""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set!")
    return value

def get_optional_env(key: str, default=None):
    """Get an optional environment variable with a default value"""
    return os.getenv(key, default)
