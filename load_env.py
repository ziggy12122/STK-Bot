
import os

def load_environment():
    """Load environment variables from .env file if it exists"""
    env_file = '.env'
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    # Also check for Replit secrets (environment variables are automatically loaded)
    # This function mainly exists for local development with .env files
    pass
