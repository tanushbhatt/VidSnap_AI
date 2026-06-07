import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Read API key from environment
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

# Create client
client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY
)

def text_to_speech_file(text, folder_name):
    folder_path = os.path.join("user_uploads", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    # Output file path
    output_path = os.path.join(folder_path, "audio.mp3")

    if not text or not text.strip():
        print("No text provided for TTS.")
        return None

    try:
        print(f"Generating TTS for {folder_name}...")
        # Generate speech
        response = client.text_to_speech.convert(
            voice_id="EXAVITQu4vr4xnSDxMaL",   # Bella voice
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2"
        )

        # Save audio
        with open(output_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print("Audio saved successfully!")
        return output_path
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None