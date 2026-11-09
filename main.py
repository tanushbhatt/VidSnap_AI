from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import uuid
from werkzeug.utils import secure_filename
import os
import threading
from text_to_audio import text_to_speech_file
from reel_generator import generate_reel
import spotify_service

UPLOAD_FOLDER = 'user_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'avi', 'mkv', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_reelflow')

# Dictionary to keep track of generation status
generation_status = {}

@app.route("/")
def home():
    return render_template("index.html")

import random

@app.route("/create", methods=["GET"])
def create():
    myid = str(uuid.uuid1())
    os.makedirs("static/songs", exist_ok=True)
    songs = os.listdir("static/songs")
    
    valid_songs = [s for s in songs if s.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg'))]
    random.shuffle(valid_songs)
    
    categories = ["Cinematic", "Travel", "Aesthetic", "Motivational", "Vlog", "Luxury"]
    suggested_songs = []
    for s in valid_songs:
        cat = random.choice(categories)
        suggested_songs.append({"filename": s, "category": cat})
    
    return render_template("create.html", myid=myid, songs=suggested_songs)

def background_generation(received_id, descrip, music_file, spotify_url):
    try:
        generation_status[received_id] = "Generating AI Voiceover..."
        if descrip:
            text_to_speech_file(descrip, received_id)
        
        music_path = None
        if spotify_url and spotify_url != "none":
            generation_status[received_id] = "Downloading Spotify Audio..."
            downloaded = spotify_service.download_preview(spotify_url, received_id)
            if downloaded:
                music_path = downloaded
                
        if not music_path and music_file and music_file != "none":
            music_path = os.path.join("static", "songs", music_file)

        generation_status[received_id] = "Generating Reel with MoviePy..."
        
        reel_filename = generate_reel(received_id, background_music_path=music_path)
        
        if reel_filename:
            generation_status[received_id] = "Completed"
        else:
            generation_status[received_id] = "Error: Failed to generate video."
            
    except Exception as e:
        print(f"Error in background generation: {e}")
        generation_status[received_id] = f"Error: {str(e)}"

@app.route("/api/spotify/search")
def spotify_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    token_info = session.get('spotify_token')
    results = spotify_service.search_tracks(query, token_info=token_info)
    return jsonify(results)

@app.route("/api/spotify/suggest", methods=["POST"])
def spotify_suggest():
    text = request.json.get('text', '').lower()
    
    # Basic keyword-based AI suggestion mapping
    if 'travel' in text or 'journey' in text:
        query = 'cinematic travel'
    elif 'gym' in text or 'workout' in text:
        query = 'energetic workout'
    elif 'chill' in text or 'aesthetic' in text or 'vlog' in text:
        query = 'aesthetic lofi vlog'
    elif 'luxury' in text or 'rich' in text:
        query = 'luxury lifestyle background'
    else:
        query = 'trending hits'
        
    token_info = session.get('spotify_token')
    results = spotify_service.search_tracks(query, token_info=token_info)
    return jsonify(results)

@app.route("/login")
def login():
    try:
        auth_url = spotify_service.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        print(f"Spotify login error: {e}")
        return redirect('/create')

@app.route("/callback")
def callback():
    try:
        code = request.args.get('code')
        if code:
            token_info = spotify_service.get_token(code)
            session['spotify_token'] = token_info
    except Exception as e:
        print(f"Spotify callback error: {e}")
    return redirect('/create')

@app.route("/api/create-reel", methods=["POST"])
def api_create_reel():
    received_id = request.form.get("uuid")
    descrip = request.form.get("text")
    music_file = request.form.get("music")
    spotify_url = request.form.get("spotify_url")
    
    if not received_id:
        received_id = str(uuid.uuid1())
        
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], received_id)
    os.makedirs(folder_path, exist_ok=True)
    
    # Save files
    files_saved = 0
    for key, file in request.files.items():
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder_path, filename))
            files_saved += 1
            
    if files_saved == 0:
        return jsonify({"success": False, "error": "No valid media files uploaded (supported: images and videos)"}), 400

    # Start generation in background
    generation_status[received_id] = "Starting..."
    thread = threading.Thread(target=background_generation, args=(received_id, descrip, music_file, spotify_url))
    thread.start()
    
    return jsonify({"success": True, "uuid": received_id})

@app.route("/api/status/<uuid_val>")
def api_status(uuid_val):
    status = generation_status.get(uuid_val, "Unknown")
    return jsonify({"status": status})

@app.route("/gallery")
def gallery():
    os.makedirs("static/reels", exist_ok=True)
    valid_video_exts = ('.mp4', '.mov', '.webm', '.avi', '.mkv')
    reels = [r for r in os.listdir("static/reels") if r.lower().endswith(valid_video_exts)]
    try:
        reels.sort(key=lambda x: os.path.getmtime(os.path.join("static/reels", x)), reverse=True)
    except Exception:
        pass
    return render_template("gallery.html", reels=reels)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs("static/reels", exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)