import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI

def authenticate_spotify():
    """Authenticates with the Spotify API using OAuth."""
    print("Authenticating with Spotify...")
    try:
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="user-library-read playlist-read-private user-top-read"
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
            artist_name = track['artists'][0]['name']  # Taking the primary artist
            album_name = track.get('album', {}).get('name', 'N/A')
            tracks_data.append({'name': track_name, 'artist': artist_name, 'album': album_name})
    return tracks_data 