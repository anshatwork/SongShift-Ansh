# spotify_to_ytmusic_transfer.py

import os
import time
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
# Get credentials from environment variables
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Path to your Google client secret file (downloaded from Google Cloud Console)
GOOGLE_CLIENT_SECRET_FILE = 'client_secret.json'
# The scopes define the permissions the script will request.
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# --- SPOTIFY FUNCTIONS ---

def authenticate_spotify():
    """Authenticates with the Spotify API using OAuth."""
    print("Authenticating with Spotify...")
    try:
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="user-library-read playlist-read-private user-top-read" # Add more scopes if needed
        )
        print("A browser window should open. If it doesn't, please manually visit the URL that will be shown.")
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user = sp.current_user()
        if user:
            print(f"Successfully authenticated with Spotify as {user['display_name']}.")
        else:
            print("Spotify authentication failed. User not found.")
            return None
        return sp
    except Exception as e:
        print(f"Error during Spotify authentication: {e}")
        print("Please ensure your SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI are correct.")
        print("Also, make sure the redirect URI is registered in your Spotify Developer Dashboard app.")
        return None

def get_spotify_playlists(sp):
    """Fetches the current user's Spotify playlists."""
    if not sp:
        return []
    playlists_data = []
    playlists = sp.current_user_playlists(limit=50)
    while playlists:
        for i, playlist in enumerate(playlists['items']):
            print(f"  Found Spotify playlist: {playlist['name']} ({len(playlist['tracks']['items'] if 'items' in playlist['tracks'] else [])} tracks initially, will fetch all)")
            playlists_data.append({'id': playlist['id'], 'name': playlist['name']})
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None
    return playlists_data

def get_spotify_playlist_tracks(sp, playlist_id):
    """Fetches all tracks from a specific Spotify playlist."""
    if not sp:
        return []
    tracks_data = []
    results = sp.playlist_items(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    for item in tracks:
        track = item.get('track')
        if track and track.get('name') and track.get('artists'):
            track_name = track['name']
            artist_name = track['artists'][0]['name'] # Taking the primary artist
            album_name = track.get('album', {}).get('name', 'N/A')
            tracks_data.append({'name': track_name, 'artist': artist_name, 'album': album_name})
    return tracks_data

# --- YOUTUBE MUSIC FUNCTIONS ---

def authenticate_youtube():
    """Authenticates with the YouTube Data API using OAuth."""
    print("\nAuthenticating with YouTube Music (Google)...")
    try:
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CLIENT_SECRET_FILE, 
            YOUTUBE_SCOPES,
            redirect_uri='http://127.0.0.1:8000/callback'
        )
        credentials = flow.run_local_server(
            port=8000,
            authorization_prompt_message='Please visit this URL to authorize this application: {url}',
            success_message='The auth flow is complete, you may close this window.',
            open_browser=True
        )
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", credentials=credentials)
        print("Successfully authenticated with YouTube.")
        return youtube
    except FileNotFoundError:
        print(f"Error: The Google client secret file '{GOOGLE_CLIENT_SECRET_FILE}' was not found.")
        print("Please download it from your Google Cloud Console and place it in the same directory as the script.")
        return None
    except Exception as e:
        print(f"Error during YouTube authentication: {e}")
        print("Make sure you've added your email as a test user in Google Cloud Console > OAuth consent screen")
        return None

def search_track_on_youtube(youtube, track_info):
    """Searches for a track on YouTube Music."""
    if not youtube:
        return None
    query = f"{track_info['name']} {track_info['artist']} {track_info['album']}"
    print(f"  Searching YouTube for: '{query}'")
    try:
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=5, # Get a few results to choose from
            type="video", # YouTube Music tracks are videos
            videoCategoryId="10" # Music category
        ).execute()

        videos = search_response.get("items", [])
        if not videos:
            print(f"    No results found on YouTube for '{query}'.")
            return None

        # Basic matching: take the first result.
        # More sophisticated matching might involve comparing duration, titles, etc.
        # Or prompting the user to choose.
        best_match = videos[0]
        video_id = best_match["id"]["videoId"]
        video_title = best_match["snippet"]["title"]
        print(f"    Found YouTube match: '{video_title}' (ID: {video_id})")
        return video_id
    except googleapiclient.errors.HttpError as e:
        print(f"    An HTTP error {e.resp.status} occurred during YouTube search: {e.content}")
        return None
    except Exception as e:
        print(f"    An error occurred during YouTube search: {e}")
        return None


def create_youtube_playlist(youtube, playlist_name):
    """Creates a new playlist on YouTube."""
    if not youtube:
        return None
    print(f"  Creating YouTube playlist: '{playlist_name}'")
    try:
        request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": f"Playlist created from Spotify by script."
                },
                "status": {
                    "privacyStatus": "private" # Or "public" or "unlisted"
                }
            }
        )
        response = request.execute()
        playlist_id = response["id"]
        print(f"    Successfully created YouTube playlist '{playlist_name}' (ID: {playlist_id}).")
        return playlist_id
    except googleapiclient.errors.HttpError as e:
        print(f"    An HTTP error {e.resp.status} occurred while creating playlist: {e.content}")
        return None
    except Exception as e:
        print(f"    An error occurred while creating playlist: {e}")
        return None

def add_track_to_youtube_playlist(youtube, playlist_id, video_id):
    """Adds a video (track) to a YouTube playlist."""
    if not youtube or not playlist_id or not video_id:
        return False
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        response = request.execute()
        print(f"    Successfully added video ID '{video_id}' to playlist ID '{playlist_id}'.")
        return True
    except googleapiclient.errors.HttpError as e:
        error_content = e.content.decode('utf-8') if isinstance(e.content, bytes) else str(e.content)
        if "playlistItemsNotAccessible" in error_content or "forbidden" in error_content.lower():
             print(f"    Error: Could not add video ID '{video_id}' to playlist ID '{playlist_id}'. This might be due to permissions or the video being unavailable.")
        elif "videoNotFound" in error_content:
            print(f"    Error: Video ID '{video_id}' not found. Cannot add to playlist.")
        else:
            print(f"    An HTTP error {e.resp.status} occurred while adding track to playlist: {error_content}")
        return False
    except Exception as e:
        print(f"    An error occurred while adding track to playlist: {e}")
        return False

# --- MAIN TRANSFER LOGIC ---

def main():
    """Main function to orchestrate the transfer."""
    print("Starting Spotify to YouTube Music transfer script...")

    # 1. Authenticate with Spotify
    sp = authenticate_spotify()
    if not sp:
        print("Exiting due to Spotify authentication failure.")
        return

    # 2. Authenticate with YouTube
    youtube = authenticate_youtube()
    if not youtube:
        print("Exiting due to YouTube authentication failure.")
        return

    # 3. Get Spotify Playlists
    print("\nFetching your Spotify playlists...")
    spotify_playlists = get_spotify_playlists(sp)
    if not spotify_playlists:
        print("No Spotify playlists found or an error occurred.")
        return

    # 4. Process each Spotify playlist
    for sp_playlist in spotify_playlists:
        print(f"\nProcessing Spotify playlist: '{sp_playlist['name']}'")

        # 4a. Get tracks from the current Spotify playlist
        spotify_tracks = get_spotify_playlist_tracks(sp, sp_playlist['id'])
        if not spotify_tracks:
            print(f"  No tracks found in Spotify playlist '{sp_playlist['name']}' or error fetching them.")
            continue

        print(f"  Found {len(spotify_tracks)} tracks in Spotify playlist '{sp_playlist['name']}'.")

        # 4b. Create a corresponding playlist on YouTube Music
        yt_playlist_id = create_youtube_playlist(youtube, sp_playlist['name'])
        if not yt_playlist_id:
            print(f"  Could not create YouTube playlist for '{sp_playlist['name']}'. Skipping this playlist.")
            continue

        # 4c. Search for each track on YouTube and add to the new YouTube playlist
        tracks_added_count = 0
        for i, track_info in enumerate(spotify_tracks):
            print(f"\n  Processing track {i+1}/{len(spotify_tracks)}: {track_info['artist']} - {track_info['name']}")
            youtube_video_id = search_track_on_youtube(youtube, track_info)
            if youtube_video_id:
                if add_track_to_youtube_playlist(youtube, yt_playlist_id, youtube_video_id):
                    tracks_added_count += 1
            else:
                print(f"    Could not find or add '{track_info['name']}' by '{track_info['artist']}' to YouTube playlist.")
            # Consider adding a small delay here to avoid hitting API rate limits
            # import time
            time.sleep(1) # Sleep for 1 second

        print(f"\nFinished processing playlist '{sp_playlist['name']}'.")
        print(f"  Added {tracks_added_count} out of {len(spotify_tracks)} tracks to YouTube playlist '{sp_playlist['name']}'.")

    print("\n--- Transfer Complete ---")
    print("Summary:")
    # You could add a more detailed summary here if needed.

if __name__ == '__main__':
    # --- Instructions for User ---
    print("---------------------------------------------------------------------------")
    print("Spotify to YouTube Music Transfer Script - Setup Instructions")
    print("---------------------------------------------------------------------------")
    print("1.  Ensure you have Python installed.")
    print("2.  Install required libraries: pip install spotipy google-api-python-client google-auth-oauthlib")
    print("3.  Spotify Setup:")
    print("    a. Go to Spotify Developer Dashboard (https://developer.spotify.com/dashboard/).")
    print("    b. Create an App (or use an existing one).")
    print("    c. Note your Client ID and Client Secret.")
    print("    d. Edit Settings: Add a Redirect URI (e.g., http://localhost:8888/callback).")
    print("    e. Update SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI in this script.")
    print("4.  Google/YouTube Setup:")
    print("    a. Go to Google Cloud Console (https://console.cloud.google.com/).")
    print("    b. Create a new project (or select an existing one).")
    print("    c. Enable the 'YouTube Data API v3'.")
    print("    d. Create OAuth 2.0 Client IDs credentials. Select 'Desktop app' for application type.")
    print("    e. Download the JSON credentials file. Rename it to 'client_secret.json' and place it in the same directory as this script.")
    print("    f. Update the GOOGLE_CLIENT_SECRET_FILE variable in this script if you named it differently.")
    print("5.  Run the script: python your_script_name.py")
    print("    You will be prompted to authenticate via your web browser for both Spotify and Google.")
    print("---------------------------------------------------------------------------")
    print("Important Considerations:")
    print("-   API Rate Limits: Both Spotify and YouTube have API rate limits. If you have many songs/playlists, the script might get temporarily blocked. Consider adding delays (e.g., time.sleep(1)) between API calls.")
    print("-   Song Matching: Song matching is not always perfect. This script uses a basic search and takes the first result. You might want to implement more sophisticated matching logic or manual confirmation for ambiguous tracks.")
    print("-   Error Handling: This script includes basic error handling, but you might want to expand it for robustness.")
    print("-   Security: NEVER share your client secrets or API keys publicly. Use environment variables or a secure config management system for production use.")
    print("---------------------------------------------------------------------------\n")

    if SPOTIPY_CLIENT_ID == 'YOUR_SPOTIFY_CLIENT_ID' or \
       SPOTIPY_CLIENT_SECRET == 'YOUR_SPOTIFY_CLIENT_SECRET' or \
       not os.path.exists(GOOGLE_CLIENT_SECRET_FILE):
        print("ERROR: Please configure your Spotify and Google API credentials in the script before running.")
        print("See the setup instructions above.")
    else:
        main()
