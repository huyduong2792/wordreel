import whisper
import os
from datetime import timedelta
import json

def format_timestamp(seconds: float):
    """Converts seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    td = timedelta(seconds=seconds)
    # Get total seconds to calculate hours, minutes, seconds
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    # Get milliseconds
    milliseconds = int(td.microseconds / 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def generate_srt(video_path, output_srt_path, model_size="medium"):
    print(f"Loading Whisper model ('{model_size}')...")
    model = whisper.load_model(model_size)
    
    print(f"Transcribing {video_path} (Language: Vietnamese)...")
    # Enable word_timestamps=True to get word-level timing
    result = model.transcribe(video_path, language="vi", task="transcribe", word_timestamps=True)
    
    segments = result["segments"]
    
    # --- New: Save word timings to JSON ---
    word_output_path = output_srt_path.replace(".srt", "_words.json")
    print(f"Writing word timestamps to {word_output_path}...")
    
    all_words = []
    for segment in segments:
        # Collect words from each segment if available
        if "words" in segment:
            all_words.extend(segment["words"])
            
    with open(word_output_path, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)
    # --------------------------------------

    print(f"Writing subtitles to {output_srt_path}...")
    with open(output_srt_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            srt_file.write(f"{i}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{text}\n\n")
            
    print("Done!")

if __name__ == "__main__":
    # You can change the filename here
    video_file = "video_100mb.mp4"
    srt_file = "test.srt"
    
    if os.path.exists(video_file):
        generate_srt(video_file, srt_file)
    else:
        print(f"Error: File {video_file} not found.")