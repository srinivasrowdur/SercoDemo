import tempfile
import io
from pydub import AudioSegment
import os

class TranscriptionAgent:
    def __init__(self, client):
        self.client = client

    def split_audio(self, audio_segment):
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

    def transcribe(self, audio_bytes, progress_callback, context=None):
        """Process audio file and return transcription"""
        try:
            if not audio_bytes:
                return "Error: No audio data received"
            
            progress_callback(0.1, "Converting audio...")
            try:
                # Load and verify audio
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                if len(audio) == 0:
                    return "Error: Audio file appears to be empty"
                
                # Convert to mono and set sample rate
                audio = audio.set_frame_rate(16000).set_channels(1)
                
                # Split into chunks
                chunks = self.split_audio(audio)
                total_chunks = len(chunks)
                
                # Process each chunk
                full_transcription = []
                
                for i, chunk in enumerate(chunks):
                    # Convert chunk to WAV
                    wav_io = io.BytesIO()
                    chunk.export(wav_io, format="wav")
                    wav_io.seek(0)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        temp_file.write(wav_io.getvalue())
                        temp_file_path = temp_file.name

                    try:
                        # Transcribe chunk
                        with open(temp_file_path, "rb") as audio_file:
                            transcription = self.client.audio.transcriptions.create(
                                model="gpt-4o-mini-transcribe",
                                file=audio_file,
                                response_format="text"
                            )
                            full_transcription.append(transcription)
                    except Exception as chunk_error:
                        return f"Error processing chunk {i+1}: {str(chunk_error)}"
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                    
                    # Update progress
                    chunk_progress = 0.1 + (0.8 * (i + 1) / total_chunks)
                    progress_callback(chunk_progress, f"Transcribing audio... ({i+1}/{total_chunks})")
                
                if not full_transcription:
                    return "Error: No chunks were successfully transcribed"
                    
                # Combine all transcriptions
                final_transcription = " ".join(full_transcription)
                progress_callback(1.0, "Transcription complete")
                
                # Store the final transcription in context
                if context is not None:
                    context['transcription'] = final_transcription
                    
                return final_transcription
                
            except Exception as e:
                return f"Error during audio conversion: {str(e)}"
                
        except Exception as e:
            return f"Error in transcription process: {str(e)}"

# Legacy agent definition can be removed 