import os
from mistralai.client import Mistral

# --- Ensure MISTRAL_API_KEY is set in your terminal session! ---
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    print("Error: MISTRAL_API_KEY environment variable not set!")
    print("Run: export MISTRAL_API_KEY='your_key_here'")
    exit(1)

# 1. Initialize the client
try:
    client = Mistral(api_key=api_key)
except Exception as e:
    print(f"Error initializing client: {e}")
    exit()

# 2. Define the prompt
messages = [
    {"role": "user", "content": "Write a very short, positive haiku about using a new API."}
]

print("--- Sending Request to Mistral ---")

# 3. Call the API
try:
    response = client.chat.complete(model="mistral-large-latest", messages=messages)

    # 4. Print the result
    print("\n--- Mistral Response ---")
    print(response.choices[0].message.content.strip())
    print("--------------------------")

except Exception as e:
    print(f"\nAn error occurred during the API call. Check your key and billing status: {e}")
