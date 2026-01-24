import google.generativeai as genai
import os

print("AI loop started ✅")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found")

genai.configure(api_key=api_key)

# Use a guaranteed-available model
model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content(
    "Say exactly: GitHub Actions can talk to Gemini"
)

print("Gemini response:")
print(response.text)
