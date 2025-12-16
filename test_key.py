import os
import requests
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

print("--- DIAGNOSTIC START ---")
if not api_key:
    print("❌ ERROR: No API Key found in .env file.")
    exit()

clean_key = api_key.strip()
print(f"🔑 Key loaded: {clean_key[:10]}...{clean_key[-5:]}")

# 1. TEST BASIC CONNECTION (List Models)
# This checks if the API is actually enabled.
print("\n📡 Test 1: Listing Available Models...")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        print("✅ SUCCESS! The API is enabled.")
        data = response.json()
        models = [m['name'].replace('models/', '') for m in data.get('models', [])]
        print("📋 Your Key can access these models:")
        for m in models:
            print(f"   - {m}")
    else:
        print(f"❌ FAILURE. Status Code: {response.status_code}")
        print(f"❌ Error Message: {response.text}")
        print("\n👇 SOLUTION 👇")
        if response.status_code == 403:
             print("Your API Key is valid, but the 'Generative Language API' is DISABLED.")
             print("Enable it here: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
        if response.status_code == 400:
             print("Your API Key format is wrong. Check for spaces or typos in .env")

except Exception as e:
    print(f"💥 Connection Error: {e}")

print("\n--- DIAGNOSTIC END ---")