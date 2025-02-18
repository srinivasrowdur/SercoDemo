import io
from pydub import AudioSegment

class AudioUtils:
    @staticmethod
    def convert_to_wav(audio_bytes):
        """Convert audio bytes to WAV format"""
        try:
            # Read directly from bytes
            audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            audio = audio.set_frame_rate(16000).set_channels(1)
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            return wav_io.read()
        except Exception as e:
            raise AudioProcessingError(
                message="Failed to convert audio to WAV format",
                error_code="AUDIO_FORMAT",
                context={'original_error': str(e)}
            )

    @staticmethod
    def split_audio(audio_segment):
        """Split audio into 5-minute chunks"""
        chunk_length_ms = 5 * 60 * 1000  # 5 minutes in milliseconds
        chunks = []
        duration_ms = len(audio_segment)
        
        # Split into 5-minute chunks
        for i in range(0, duration_ms, chunk_length_ms):
            chunk = audio_segment[i:i + chunk_length_ms]
            # Convert to mono and set sample rate to reduce file size
            chunk = chunk.set_channels(1).set_frame_rate(16000)
            chunks.append(chunk)
        
        return chunks

    @staticmethod
    def prepare_audio_for_transcription(audio_bytes):
        """Prepare audio for transcription by converting to mono and setting sample rate"""
        try:
            # Convert input audio to AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            
            # Convert to mono and set sample rate to reduce file size
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            return audio
        except Exception as e:
            raise AudioProcessingError(
                message="Failed to prepare audio for transcription",
                error_code="AUDIO_PREP",
                context={'original_error': str(e)}
            )