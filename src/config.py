import os
from typing import Dict

from dotenv import load_dotenv

# Add model configurations
LLM_MODELS = {
    'basic': 'gpt-4o-mini',
    'advanced': 'gpt-4o',
    'reasoning': 'o1-preview',
    'embeddings': 'text-embedding-3-small'
}

def load_config() -> Dict[str, str]:
    """Load configuration, prioritizing .env file over environment variables"""
    # First, store any existing env vars we want to override
    existing_vars = {}
    for key in ['ZENROWS_API_KEY', 'OPENAI_API_KEY', 'LANGCHAIN_API_KEY', 'NOTION_API_KEY', 'PINECONE_API_KEY']:
        if key in os.environ:
            existing_vars[key] = os.environ[key]
            del os.environ[key]
    
    # Now load .env file
    load_dotenv(override=True)
    
    # Create config dictionary with added models
    config = {
        'ZENROWS_API_KEY': os.getenv('ZENROWS_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'LANGCHAIN_API_KEY': os.getenv('LANGCHAIN_API_KEY'),
        'NOTION_API_KEY': os.getenv('NOTION_API_KEY'),
        'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY'),
        'LLM_MODELS': LLM_MODELS
    }
    
    # Restore original env vars if needed
    for key, value in existing_vars.items():
        os.environ[key] = value
    
    return config

# Create a global config object
config = load_config()
