import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import uuid
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

print(f"DEBUG: Loading .env from {env_path}")
print(f"DEBUG: SPOTIPY_CLIENT_ID is {'SET' if os.environ.get('SPOTIPY_CLIENT_ID') else 'MISSING'}")

# Read from environment variables
SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI', 'http://localhost:5000/callback')

def get_auth_url():
    """Return the Spotify login URL"""
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-library-read"
    )
    return sp_oauth.get_authorize_url()

def get_token(code):
    """Get token from authorization code"""
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-library-read"
    )
    token_info = sp_oauth.get_access_token(code)
    return token_info

def get_spotify_client(token_info=None):
    if token_info:
        print("DEBUG: Using Spotify token from session.")
        return spotipy.Spotify(auth=token_info['access_token'])
    elif SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
        print("DEBUG: Using Spotify Client Credentials flow.")
        auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
        return spotipy.Spotify(auth_manager=auth_manager)
    print("DEBUG: WARNING: No Spotify credentials found!")
    return None

def search_tracks(query, limit=10, token_info=None):
    """Search Spotify for tracks based on query, with iTunes fallback."""
    client = get_spotify_client(token_info)
    
    # Try Spotify first
    if client:
        try:
            print(f"DEBUG: Executing Spotify search for query: '{query}'")
            results = client.search(q=query, limit=limit, type='track')
            tracks = []
            for item in results.get('tracks', {}).get('items', []):
                # Only include tracks that have a preview_url
                if item.get('preview_url'):
                    artists = item.get('artists', [])
                    artist_name = artists[0].get('name', 'Unknown Artist') if artists else "Unknown Artist"
                    images = item.get('album', {}).get('images', [])
                    album_cover = images[1]['url'] if len(images) > 1 else (images[0]['url'] if images else "")
                    track_info = {
                        'id': item.get('id', ''),
                        'name': item.get('name', 'Unknown Track'),
                        'artist': artist_name,
                        'album_cover': album_cover,
                        'preview_url': item.get('preview_url'),
                        'duration_ms': item.get('duration_ms', 30000)
                    }
                    tracks.append(track_info)
            print(f"DEBUG: Found {len(tracks)} tracks with preview_urls out of {len(results.get('tracks', {}).get('items', []))} total Spotify results.")
            if tracks:
                return tracks
        except Exception as e:
            print(f"DEBUG: Spotify search failed (likely Premium required): {e}")
            print("DEBUG: Falling back to iTunes Search API...")
            
    # iTunes Fallback
    try:
        print(f"DEBUG: Executing iTunes search for query: '{query}'")
        import urllib.parse
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit={limit}"
        response = requests.get(url, timeout=5)
        data = response.json()
        tracks = []
        for item in data.get('results', []):
            if item.get('previewUrl'):
                track_info = {
                    'id': str(item.get('trackId', '')),
                    'name': item.get('trackName', 'Unknown Track'),
                    'artist': item.get('artistName', 'Unknown Artist'),
                    'album_cover': item.get('artworkUrl100', ''),
                    'preview_url': item.get('previewUrl'),
                    'duration_ms': item.get('trackTimeMillis', 30000)
                }
                tracks.append(track_info)
        print(f"DEBUG: Found {len(tracks)} tracks on iTunes.")
        return tracks
    except Exception as e:
        print(f"DEBUG: iTunes fallback failed: {e}")
        return []

def download_preview(preview_url, folder_name):
    """Download the 30-second Spotify preview MP3 to the user's upload folder."""
    if not preview_url:
        return None
        
    try:
        print(f"Downloading Spotify preview from {preview_url}")
        response = requests.get(preview_url, stream=True, timeout=15)
        response.raise_for_status()
        
        # Save to user's folder
        folder_path = os.path.join("user_uploads", folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, "spotify_bg.mp3")
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Spotify preview saved to {file_path}")
        return file_path
    except Exception as e:
        print(f"Failed to download Spotify preview: {e}")
        return None
