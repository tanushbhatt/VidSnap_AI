import os
from PIL import Image
from moviepy import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, CompositeVideoClip

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

def prepare_video(clip, target_size=(1080, 1920)):
    try:
        target_w, target_h = target_size
        clip_w, clip_h = clip.size
        clip_ratio = clip_w / clip_h
        target_ratio = target_w / target_h

        if clip_ratio > target_ratio:
            new_w = target_w
            new_h = int(new_w / clip_ratio)
        else:
            new_h = target_h
            new_w = int(new_h * clip_ratio)

        resized_clip = clip.resized(new_size=(new_w, new_h))
        return CompositeVideoClip([resized_clip.with_position("center")], size=target_size)
    except Exception as e:
        print(f"Error preparing video clip: {e}")
        return clip

def generate_reel(folder_name, background_music_path=None, duration_per_image=3):
    print(f"Starting reel generation for {folder_name}...")
    folder_path = os.path.join("user_uploads", folder_name)
    output_path = os.path.join("static", "reels", f"{folder_name}.mp4")
    
    # 1. Get all media files (images and videos)
    valid_image_exts = {'.png', '.jpg', '.jpeg', '.webp'}
    valid_video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    
    if not os.path.exists(folder_path):
        print("Upload folder does not exist:", folder_path)
        return None

    files = os.listdir(folder_path)
    media_files = [
        f for f in files 
        if not f.endswith("_temp.jpg") 
        and not f.startswith("audio.") 
        and not f.startswith("spotify_bg.")
        and (os.path.splitext(f)[1].lower() in valid_image_exts or os.path.splitext(f)[1].lower() in valid_video_exts)
    ]
    media_files.sort()
    
    if not media_files:
        print("No valid media found in", folder_path)
        return None
        
    print(f"Found {len(media_files)} media files.")

    # Check for TTS audio beforehand to adjust image duration if needed
    tts_path = os.path.join(folder_path, "audio.mp3")
    tts_clip = None
    if os.path.exists(tts_path):
        try:
            tts_clip = AudioFileClip(tts_path)
            # If voiceover is longer than total default duration of image slides, adapt duration
            num_image_files = sum(1 for f in media_files if os.path.splitext(f)[1].lower() in valid_image_exts)
            if num_image_files > 0 and tts_clip.duration > (num_image_files * duration_per_image):
                duration_per_image = max(duration_per_image, tts_clip.duration / num_image_files)
        except Exception as e:
            print(f"Could not inspect TTS audio duration: {e}")
    
    # 2. Process media and create clips
    clips = []
    temp_files = []
    final_video = None
    audio_clips = []
    
    try:
        for media_file in media_files:
            file_path = os.path.join(folder_path, media_file)
            ext = os.path.splitext(media_file)[1].lower()
            
            if ext in valid_image_exts:
                processed_img_path = prepare_image(file_path)
                if processed_img_path:
                    temp_files.append(processed_img_path)
                    try:
                        clip = ImageClip(processed_img_path).with_duration(duration_per_image)
                        clips.append(clip)
                    except Exception as e:
                        print(f"Error creating clip for image {media_file}: {e}")
            elif ext in valid_video_exts:
                try:
                    vclip = VideoFileClip(file_path)
                    prepared_vclip = prepare_video(vclip)
                    clips.append(prepared_vclip)
                except Exception as e:
                    print(f"Error creating clip for video {media_file}: {e}")
                    
        if not clips:
            print("Failed to create any video clips.")
            return None
            
        print("Concatenating clips...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 3. Handle Audio
        if tts_clip:
            print("Adding AI Voiceover...")
            audio_clips.append(tts_clip)
            
        if background_music_path and os.path.exists(background_music_path):
            print(f"Adding Background Music: {background_music_path}...")
            try:
                bg_clip = AudioFileClip(background_music_path)
                
                # Trim bg music to video duration if it's longer
                if bg_clip.duration > final_video.duration:
                    bg_clip = bg_clip.subclipped(0, final_video.duration)
                    
                # Lower volume of background music if TTS voiceover is present
                if tts_clip:
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
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )
        print(f"Reel successfully generated: {output_path}")
        return f"{folder_name}.mp4"
        
    except Exception as e:
        print(f"Error exporting video: {e}")
        return None
        
    finally:
        # Cleanup video & audio clips to release Windows file locks
        try:
            if final_video:
                final_video.close()
            for c in clips:
                c.close()
            for a in audio_clips:
                a.close()
        except Exception:
            pass
            
        # Cleanup temporary generated images
        for temp_p in temp_files:
            if os.path.exists(temp_p):
                try:
                    os.remove(temp_p)
                except Exception:
                    pass
