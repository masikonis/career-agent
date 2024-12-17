from dotenv import load_dotenv
import os
import openai
from langsmith.wrappers import wrap_openai
from langsmith import traceable

def main():
    # Load environment variables
    load_dotenv()
    
    # Wrap the OpenAI client
    client = wrap_openai(openai.Client(api_key=os.getenv('OPENAI_API_KEY')))
    
    @traceable
    def chat_pipeline(user_input: str):
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": user_input}],
            model="gpt-4o-mini"
        )
        return response.choices[0].message.content
    
    # Test the chat pipeline
    print(chat_pipeline("Say hello!"))

if __name__ == "__main__":
    main()
