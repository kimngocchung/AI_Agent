"""
Configuration Manager
Handle .env file operations and connection testing
"""

import os
from dotenv import load_dotenv, set_key, find_dotenv
import requests
from google import generativeai as genai

def save_to_env(key: str, value: str) -> bool:
    """
    Save a key-value pair to .env file
    
    Args:
        key: Environment variable name
        value: Value to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        env_file = find_dotenv()
        if not env_file:
            # Create .env if doesn't exist
            env_file = os.path.join(os.getcwd(), '.env')
            with open(env_file, 'w') as f:
                f.write("")
        
        set_key(env_file, key, value)
        return True
    except Exception as e:
        print(f"Error saving to .env: {e}")
        return False

def load_from_env(key: str) -> str:
    """
    Load a value from .env file
    
    Args:
        key: Environment variable name
        
    Returns:
        Value from .env or empty string
    """
    load_dotenv()
    return os.getenv(key, "")

def test_gemini_connection(api_key: str) -> tuple[bool, str]:
    """
    Test Gemini API connection
    
    Args:
        api_key: Gemini API key
        
    Returns:
        (success: bool, message: str)
    """
    try:
        genai.configure(api_key=api_key)
        # Try to list models to verify connection
        models = genai.list_models()
        return True, "✅ Gemini API connected successfully"
    except Exception as e:
        return False, f"❌ Gemini API connection failed: {str(e)}"

def test_kali_connection(url: str) -> tuple[bool, str]:
    """
    Test Kali Listener connection
    
    Args:
        url: Kali Listener URL
        
    Returns:
        (success: bool, message: str)
    """
    try:
        # Try to ping the health endpoint
        response = requests.get(f"{url}/", timeout=5)
        if response.status_code == 200:
            return True, "✅ Kali Listener connected"
        else:
            return False, f"❌ Kali Listener returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "❌ Cannot connect to Kali Listener (connection refused)"
    except requests.exceptions.Timeout:
        return False, "❌ Kali Listener connection timeout"
    except Exception as e:
        return False, f"❌ Kali Listener error: {str(e)}"
