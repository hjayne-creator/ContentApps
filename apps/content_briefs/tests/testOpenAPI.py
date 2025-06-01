import os
from dotenv import load_dotenv
import openai
from config import Config

# Load .env file
load_dotenv()

# Load API key from environment variable
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError('OPENAI_API_KEY environment variable not set')

client = openai.OpenAI(api_key=api_key)

prompt = "Say hello from OpenAI!"

try:
    response = client.chat.completions.create(
        model=Config.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0.5
    )
    print("OpenAI response:", response.choices[0].message.content.strip())
except Exception as e:
    print("OpenAI API error:", e) 