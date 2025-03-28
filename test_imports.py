print("Testing imports...")
import streamlit
print("✅ Streamlit imported successfully")

from google import genai
print("✅ google.genai imported successfully")
print(f"genai version: {genai.__version__}")

import sys
print(f"Python path: {sys.path}") 