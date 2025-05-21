import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Spotify Configuration
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# YouTube Configuration
GOOGLE_CLIENT_SECRET_FILE = 'client_secret.json'
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Batch Processing Configuration
SEARCH_BATCH_SIZE = 50
UPLOAD_BATCH_SIZE = 50 