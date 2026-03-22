import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# 🔥 GROQ (Recommended)
def ask_groq(prompt):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY not set in environment variables")
    
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise Exception(f"Groq API error ({response.status_code}): {response.text}")
    
    result = response.json()
    if 'choices' not in result or not result['choices']:
        raise Exception(f"Unexpected Groq API response: {result}")
    
    return result['choices'][0]['message']['content']


# 🤖 HUGGING FACE (Inference Providers, router endpoint)
# Note: api-inference.huggingface.co is now deprecated and returns 410.
# Use router.huggingface.co with OpenAI-compatible chat completions API.
HF_MODEL = "openai/gpt-oss-120b:fastest"

def ask_huggingface(prompt):
    API_URL = "https://router.huggingface.co/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": HF_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7
    }

    response = requests.post(API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()

    # Return the assistant reply text (fall back safely)
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")


# 🌟 GEMINI (UPDATED VERSION)
def ask_gemini(prompt):
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise Exception(f"Gemini dependencies not installed: {str(e)}")
    
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set")
    
    genai.configure(api_key=GEMINI_API_KEY)

    # Using gemini-2.5-flash for faster and better responses
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)

    return response.text