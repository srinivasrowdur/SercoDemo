from swarm import Swarm
from openai import OpenAI
from .transcription_agent import TranscriptionAgent
from .conversation_agent import ConversationAgent

class Orchestrator:
    def __init__(self, client):
        self.client = client
        self.transcription_agent = TranscriptionAgent(client)
        self.conversation_agent = ConversationAgent(client)

    def process_transcription(self, audio_bytes, progress_callback):
        """Coordinate transcription of audio using the transcription agent"""
        return self.transcription_agent.transcribe(audio_bytes, progress_callback)

    def process_conversation(self, transcription_text, progress_callback):
        """Coordinate conversation generation using the conversation agent"""
        if not callable(progress_callback):
            # Create a no-op callback if none provided
            progress_callback = lambda p, t: None
        return self.conversation_agent.generate_conversation(transcription_text, progress_callback)

    def process_audio(self, input_data, progress_callback):
        """Legacy method - kept for backward compatibility"""
        if isinstance(input_data, str):
            # If input is text, assume it's transcription and generate conversation
            return self.process_conversation(input_data, progress_callback)
        else:
            # If input is bytes, assume it's audio and do transcription
            return self.process_transcription(input_data, progress_callback)

    # Remove or deprecate process_audio_new as it's using the old swarm approach 