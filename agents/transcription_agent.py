from swarm import Swarm, Agent
import tempfile
import io
from pydub import AudioSegment
import os

class TranscriptionAgent:
    def __init__(self, client):
        self.client = client

    def transcribe(self, audio_bytes, progress_callback):
        """Process audio file and return transcription"""
        try:
            # Verify we have audio bytes
            if not audio_bytes:
                return "Error: No audio data received"
            
            progress_callback(0.1, "Converting audio...")
            try:
                # Load and verify audio
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                if len(audio) == 0:
                    return "Error: Audio file appears to be empty"
                
                # Convert to WAV with specific parameters
                audio = audio.set_frame_rate(16000).set_channels(1)
            except Exception as e:
                return f"Error during audio conversion: {str(e)}"

            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    # Export with explicit parameters
                    audio.export(
                        temp_file.name,
                        format="wav",
                        parameters=["-ac", "1", "-ar", "16000"]
                    )
                    
                    progress_callback(0.3, "Transcribing audio...")
                    
                    # Open and verify the temp file
                    if not os.path.exists(temp_file.name):
                        return "Error: Failed to create temporary file"
                        
                    if os.path.getsize(temp_file.name) == 0:
                        return "Error: Temporary file is empty"
                    
                    # Perform transcription
                    with open(temp_file.name, "rb") as audio_file:
                        try:
                            transcription = self.client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file,
                                response_format="text"
                            )
                            
                            # Verify transcription result
                            if not transcription:
                                return "Error: No transcription returned from API"
                                
                            progress_callback(1.0, "Transcription complete")
                            return transcription
                            
                        except Exception as e:
                            return f"Error during OpenAI API call: {str(e)}"
                        
            except Exception as e:
                return f"Error handling temporary file: {str(e)}"
            finally:
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.remove(temp_file.name)
                    
        except Exception as e:
            return f"Error in transcription process: {str(e)}"

# Legacy agent definition
agent = Agent(
    name="Transcription Agent",
    instructions="You are an expert audio transcription agent.",
    functions=[lambda audio_bytes: TranscriptionAgent(None).transcribe(audio_bytes, lambda p, t: None)],
) 