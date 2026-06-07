import os
from PIL import Image
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip

def prepare_image(img_path, target_size=(1080, 1920)):
    try:
        img = Image.open(img_path).convert("RGB")
        target_w, target_h = target_size
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            new_w = target_w
            new_h = int(new_w / img_ratio)
        else:
            new_h = target_h
            new_w = int(new_h * img_ratio)
            
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        new_img = Image.new("RGB", target_size, (0, 0, 0))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        new_img.paste(img, (paste_x, paste_y))
        
        temp_path = img_path + "_temp.jpg"
        new_img.save(temp_path)
        return temp_path
    except Exception as e:
        print(f"Error preparing image {img_path}: {e}")
        return None

def generate_reel(folder_name, background_music_path=None, duration_per_image=3):
    print(f"Starting reel generation for {folder_name}...")
    folder_path = os.path.join("user_uploads", folder_name)
    output_path = os.path.join("static", "reels", f"{folder_name}.mp4")
    
    # 1. Get all images
    valid_exts = {'.png', '.jpg', '.jpeg'}
    files = os.listdir(folder_path)
    image_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_exts and not f.endswith("_temp.jpg")]
    image_files.sort()
    
    if not image_files:
        print("No images found in", folder_path)
        return None
        
    print(f"Found {len(image_files)} images.")
    
    # 2. Process images and create clips
    clips = []
    for img_file in image_files:
        img_path = os.path.join(folder_path, img_file)
        processed_img_path = prepare_image(img_path)
        if processed_img_path:
            try:
                # Use moviepy 2.x method: with_duration
                clip = ImageClip(processed_img_path).with_duration(duration_per_image)
                clips.append(clip)
            except Exception as e:
                print(f"Error creating clip for {img_file}: {e}")
                
    if not clips:
        print("Failed to create any video clips.")
        return None
        
    print("Concatenating clips...")
    # 3. Concatenate clips
    final_video = concatenate_videoclips(clips, method="compose")
    
    # 4. Handle Audio
    audio_clips = []
    
    # Check for TTS audio
    tts_path = os.path.join(folder_path, "audio.mp3")
    if os.path.exists(tts_path):
        print("Adding AI Voiceover...")
        try:
            tts_clip = AudioFileClip(tts_path)
            audio_clips.append(tts_clip)
        except Exception as e:
            print(f"Failed to load TTS audio: {e}")
        
    # Check for background music
    if background_music_path and os.path.exists(background_music_path):
        print(f"Adding Background Music: {background_music_path}...")
        try:
            bg_clip = AudioFileClip(background_music_path)
            
            # Trim bg music to video duration if it's longer
            if bg_clip.duration > final_video.duration:
                # MoviePy 2 uses subclipped
                bg_clip = bg_clip.subclipped(0, final_video.duration)
                
            # Lower volume of background music if TTS is present
            if os.path.exists(tts_path):
                try:
                    from moviepy.audio.fx import MultiplyVolume
                    bg_clip = bg_clip.with_effects([MultiplyVolume(0.3)])
                except Exception as e:
                    print(f"Could not adjust volume: {e}")
                    
            audio_clips.append(bg_clip)
        except Exception as e:
            print(f"Failed to load background music: {e}")
        
    if audio_clips:
        if len(audio_clips) > 1:
            final_audio = CompositeAudioClip(audio_clips)
        else:
            final_audio = audio_clips[0]
        final_video = final_video.with_audio(final_audio)
        
    print("Exporting video...")
    # 5. Export
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )
        print(f"Reel successfully generated: {output_path}")
    except Exception as e:
        print(f"Error exporting video: {e}")
        return None
    
    # Cleanup temp images
    for img_file in image_files:
        temp_path = os.path.join(folder_path, img_file) + "_temp.jpg"
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return f"{folder_name}.mp4"
