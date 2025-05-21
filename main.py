from spotify_api import authenticate_spotify, get_spotify_playlists, get_spotify_playlist_tracks
from youtube_api import (
    authenticate_youtube,
    create_youtube_playlist,
    search_multiple_tracks_on_youtube,
    bulk_add_tracks_to_youtube_playlist
)

def print_instructions():
    """Prints setup instructions for the user."""
    print("---------------------------------------------------------------------------")
    print("Spotify to YouTube Music Transfer Script - Setup Instructions")
    print("---------------------------------------------------------------------------")
    print("1.  Ensure you have Python installed.")
    print("2.  Install required libraries: pip install spotipy google-api-python-client google-auth-oauthlib python-dotenv")
    print("3.  Spotify Setup:")
    print("    a. Go to Spotify Developer Dashboard (https://developer.spotify.com/dashboard/).")
    print("    b. Create an App (or use an existing one).")
    print("    c. Note your Client ID and Client Secret.")
    print("    d. Edit Settings: Add a Redirect URI (e.g., http://localhost:8888/callback).")
    print("    e. Create a .env file with your Spotify credentials:")
    print("       SPOTIPY_CLIENT_ID=your_client_id")
    print("       SPOTIPY_CLIENT_SECRET=your_client_secret")
    print("       SPOTIPY_REDIRECT_URI=your_redirect_uri")
    print("4.  Google/YouTube Setup:")
    print("    a. Go to Google Cloud Console (https://console.cloud.google.com/).")
    print("    b. Create a new project (or select an existing one).")
    print("    c. Enable the 'YouTube Data API v3'.")
    print("    d. Create OAuth 2.0 Client IDs credentials. Select 'Desktop app' for application type.")
    print("    e. Download the JSON credentials file. Rename it to 'client_secret.json' and place it in the same directory.")
    print("5.  Run the script: python main.py")
    print("    You will be prompted to authenticate via your web browser for both Spotify and Google.")
    print("---------------------------------------------------------------------------")
    print("Important Considerations:")
    print("-   API Rate Limits: Both Spotify and YouTube have API rate limits.")
    print("-   Song Matching: Song matching uses basic title and artist matching.")
    print("-   Security: NEVER share your client secrets or API keys publicly.")
    print("---------------------------------------------------------------------------\n")

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

        # 4c. Search for tracks in batches
        search_results = search_multiple_tracks_on_youtube(youtube, spotify_tracks)
        
        # Extract video IDs from search results
        video_ids = [search_results.get(f"{track['name']} {track['artist']} {track['album']}")
                    for track in spotify_tracks]
        
        # 4d. Bulk add tracks to the playlist
        tracks_added_count = bulk_add_tracks_to_youtube_playlist(youtube, yt_playlist_id, video_ids)

        print(f"\nFinished processing playlist '{sp_playlist['name']}'.")
        print(f"  Added {tracks_added_count} out of {len(spotify_tracks)} tracks to YouTube playlist '{sp_playlist['name']}'.")

    print("\n--- Transfer Complete ---")

if __name__ == '__main__':
    print_instructions()
    main() 