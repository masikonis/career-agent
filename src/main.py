from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def main():
    # Load environment variables
    load_dotenv()
    
    # Debug: Print first few chars of keys
    openai_key = os.getenv('OPENAI_API_KEY', 'not set')
    langchain_key = os.getenv('LANGCHAIN_API_KEY', 'not set')
    
    print(f"OPENAI_API_KEY starts with: {openai_key[:7]}...")
    print(f"LANGCHAIN_API_KEY starts with: {langchain_key[:7]}...")
    
    # Initialize chat model
    chat = ChatOpenAI()
    
    # Simple test message
    messages = [HumanMessage(content="Say hello!")]
    response = chat.invoke(messages)
    print(response.content)

if __name__ == "__main__":
    main()
