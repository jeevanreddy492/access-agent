import os

GCP_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]   # your project id
GCP_LOCATION = "global"
MODEL_NAME = "gemini-3.5-flash-lite"
MAX_STEPS = 6
APP_NAME = "access_agent"

# ADK reads these to connect to Vertex AI.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", GCP_LOCATION)