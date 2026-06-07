import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {CLIENT_SECRET}")

try:
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    results = sp.search(q='skyfall', limit=5, type='track')
    for item in results['tracks']['items']:
        print(f"Found: {item['name']} by {item['artists'][0]['name']}, preview: {item.get('preview_url')}")
except Exception as e:
    print(f"ERROR: {e}")
