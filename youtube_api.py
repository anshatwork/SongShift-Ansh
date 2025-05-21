import os
import time
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from config import GOOGLE_CLIENT_SECRET_FILE, YOUTUBE_SCOPES, SEARCH_BATCH_SIZE, UPLOAD_BATCH_SIZE

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
                    "privacyStatus": "private"
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

def search_multiple_tracks_on_youtube(youtube, tracks_info, batch_size=None):
    """Searches for multiple tracks on YouTube Music in a single query."""
    if not youtube:
        return {}

    batch_size = batch_size or SEARCH_BATCH_SIZE
    results = {}

    for i in range(0, len(tracks_info), batch_size):
        batch = tracks_info[i:i + batch_size]
        print(f"\nProcessing batch {(i//batch_size) + 1} ({len(batch)} tracks)")
        
        combined_query = " OR ".join([
            f'"{track["name"]}" "{track["artist"]}"'
            for track in batch
        ])
        
        print(f"  Searching YouTube for batch of {len(batch)} songs")
        try:
            search_response = youtube.search().list(
                q=combined_query,
                part="id,snippet",
                maxResults=len(batch),
                type="video",
                videoCategoryId="10"
            ).execute()

            videos = search_response.get("items", [])
            if not videos:
                print(f"    No results found for this batch.")
                continue

            for video in videos:
                video_title = video["snippet"]["title"].lower()
                video_id = video["id"]["videoId"]
                
                for track in batch:
                    track_name = track["name"].lower()
                    artist_name = track["artist"].lower()
                    
                    if track_name in video_title and artist_name in video_title:
                        query = f"{track['name']} {track['artist']} {track['album']}"
                        if query not in results:
                            results[query] = video_id
                            print(f"    Matched: '{track['name']}' by '{track['artist']}' to '{video['snippet']['title']}' (ID: {video_id})")

        except googleapiclient.errors.HttpError as e:
            print(f"    An HTTP error {e.resp.status} occurred during YouTube search: {e.content}")
        except Exception as e:
            print(f"    An error occurred during YouTube search: {e}")
        
        time.sleep(1)
    
    return results

def bulk_add_tracks_to_youtube_playlist(youtube, playlist_id, video_ids, batch_size=None):
    """Adds multiple videos (tracks) to a YouTube playlist in bulk."""
    if not youtube or not playlist_id or not video_ids:
        return 0

    batch_size = batch_size or UPLOAD_BATCH_SIZE
    successful_adds = 0
    
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        print(f"\nAdding batch of {len(batch)} tracks to playlist...")
        
        batch_request = youtube.new_batch_http_request()
        
        for video_id in batch:
            if video_id:
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
                batch_request.add(request)
        
        try:
            batch_request.execute()
            successful_adds += len(batch)
            print(f"  Successfully added {len(batch)} tracks to playlist.")
        except googleapiclient.errors.HttpError as e:
            error_content = e.content.decode('utf-8') if isinstance(e.content, bytes) else str(e.content)
            print(f"  Error adding batch to playlist: {error_content}")
        except Exception as e:
            print(f"  An error occurred while adding batch to playlist: {e}")
        
        time.sleep(1)
    
    return successful_adds 