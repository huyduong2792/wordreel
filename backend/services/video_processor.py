"""
Video processing service for transcription and subtitle generation using AssemblyAI
"""
import os
import json
import tempfile
import subprocess
from typing import List, Optional
import assemblyai as aai
from models.schemas import Subtitle, WordTiming, TemplateConfig, TemplateType
from config import get_settings


class VideoProcessor:
    """Process videos for subtitle extraction and generation using AssemblyAI"""
    
    def __init__(self):
        """Initialize video processor with AssemblyAI"""
        settings = get_settings()
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        self._transcriber = None
    
    def _get_transcriber(self):
        """Get AssemblyAI transcriber lazily"""
        if self._transcriber is None:
            self._transcriber = aai.Transcriber()
        return self._transcriber
    
    def get_video_info(self, video_path: str) -> dict:
        """Get video metadata"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe = json.loads(result.stdout)
            
            video_info = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            duration = float(probe['format']['duration'])
            width = int(video_info['width'])
            height = int(video_info['height'])
            
            return {
                "duration": duration,
                "width": width,
                "height": height,
                "format": probe['format']['format_name']
            }
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from video"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
        
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '16k',
                '-y',  # Overwrite output
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except Exception as e:
            raise Exception(f"Failed to extract audio: {str(e)}")
    
    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en",
        **kwargs
    ) -> List[Subtitle]:
        """Transcribe audio to subtitles with word timings using AssemblyAI"""
        transcriber = self._get_transcriber()
        
        try:
            # Configure transcription with word-level timestamps
            config = aai.TranscriptionConfig(
                language_code=language,
                punctuate=True,
                format_text=True,
                # Enable word-level timestamps (included by default)
                # Enable auto chapters for better segmentation
                auto_chapters=False,
                # Speaker diarization (optional - useful for conversations)
                speaker_labels=False,
            )
            
            # Transcribe audio file
            transcript = transcriber.transcribe(audio_path, config=config)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            
            subtitles = []
            
            # Process sentences/utterances for better subtitle segmentation
            if transcript.utterances:
                # Use utterances if available (better for conversations)
                for i, utterance in enumerate(transcript.utterances):
                    word_timings = []
                    for word in utterance.words:
                        word_timings.append(WordTiming(
                            word=word.text,
                            start=word.start / 1000.0,  # Convert ms to seconds
                            end=word.end / 1000.0
                        ))
                    
                    subtitle = Subtitle(
                        subtitle_id=f"subtitle-{i + 1}",
                        template_config=TemplateConfig(
                            type=TemplateType.COLOR_HIGHLIGHT
                        ),
                        text=utterance.text,
                        start_time=utterance.start / 1000.0,
                        end_time=utterance.end / 1000.0,
                        word_timings=word_timings
                    )
                    subtitles.append(subtitle)
            else:
                # Fall back to sentence-based segmentation from words
                words = transcript.words or []
                if words:
                    subtitles = self._segment_words_to_subtitles(words)
            
            return subtitles
            
        except Exception as e:
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    def _segment_words_to_subtitles(
        self,
        words: list,
        max_words_per_subtitle: int = 10,
        max_duration: float = 5.0
    ) -> List[Subtitle]:
        """Segment words into subtitle chunks"""
        subtitles = []
        current_words = []
        current_start = None
        subtitle_count = 0
        
        for word in words:
            if current_start is None:
                current_start = word.start / 1000.0
            
            current_words.append(word)
            current_end = word.end / 1000.0
            current_duration = current_end - current_start
            
            # Check if we should create a new subtitle
            should_break = (
                len(current_words) >= max_words_per_subtitle or
                current_duration >= max_duration or
                (word.text and word.text[-1] in '.!?')
            )
            
            if should_break:
                subtitle_count += 1
                word_timings = [
                    WordTiming(
                        word=w.text,
                        start=w.start / 1000.0,
                        end=w.end / 1000.0
                    )
                    for w in current_words
                ]
                
                subtitle = Subtitle(
                    subtitle_id=f"subtitle-{subtitle_count}",
                    template_config=TemplateConfig(
                        type=TemplateType.COLOR_HIGHLIGHT
                    ),
                    text=" ".join(w.text for w in current_words),
                    start_time=current_start,
                    end_time=current_end,
                    word_timings=word_timings
                )
                subtitles.append(subtitle)
                
                current_words = []
                current_start = None
        
        # Handle remaining words
        if current_words:
            subtitle_count += 1
            word_timings = [
                WordTiming(
                    word=w.text,
                    start=w.start / 1000.0,
                    end=w.end / 1000.0
                )
                for w in current_words
            ]
            
            subtitle = Subtitle(
                subtitle_id=f"subtitle-{subtitle_count}",
                template_config=TemplateConfig(
                    type=TemplateType.COLOR_HIGHLIGHT
                ),
                text=" ".join(w.text for w in current_words),
                start_time=current_start,
                end_time=current_words[-1].end / 1000.0,
                word_timings=word_timings
            )
            subtitles.append(subtitle)
        
        return subtitles
    
    def process_video(
        self,
        video_path: str,
        language: str = "en"
    ) -> dict:
        """Process video: extract info and generate subtitles"""
        try:
            # Get video info
            video_info = self.get_video_info(video_path)
            
            # Extract audio
            audio_path = self.extract_audio(video_path)
            
            # Transcribe
            subtitles = self.transcribe_audio(audio_path, language)
            
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "info": video_info,
                "subtitles": [sub.dict() for sub in subtitles]
            }
            
        except Exception as e:
            raise Exception(f"Failed to process video: {str(e)}")
    
    def convert_to_hls(self, input_path: str, output_dir: str) -> str:
        """Convert video to HLS format"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            playlist_path = os.path.join(output_dir, "playlist.m3u8")
            segment_path = os.path.join(output_dir, 'segment%d.ts')
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-f', 'hls',
                '-start_number', '0',
                '-hls_time', '10',
                '-hls_list_size', '0',
                '-hls_segment_filename', segment_path,
                '-y',
                playlist_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return playlist_path
            
        except Exception as e:
            raise Exception(f"Failed to convert to HLS: {str(e)}")
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        time_offset: float = 1.0
    ) -> str:
        """Generate thumbnail from video"""
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(time_offset),
                '-i', video_path,
                '-vf', 'scale=480:-1',
                '-vframes', '1',
                '-y',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
            
        except Exception as e:
            raise Exception(f"Failed to generate thumbnail: {str(e)}")

