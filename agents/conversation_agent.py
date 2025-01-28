from swarm import Swarm, Agent

class ConversationAgent:
    def __init__(self, client):
        self.client = client

    def generate_conversation(self, text, progress_callback):
        """Convert transcription to conversation format"""
        try:
            if not text:
                return "Error: No transcription text provided"

            # Safe progress update
            try:
                if callable(progress_callback):
                    progress_callback(0.2, "Generating conversation...")
            except Exception as e:
                print(f"Progress callback error: {e}")  # Log but continue

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert medical transcriptionist with years of experience in documenting clinical conversations. 
                        Your task is to convert the text into a precise dialogue format, maintaining all medical terminology and clinical details."""
                    },
                    {"role": "user", "content": text}
                ]
            )

            # Safe progress update
            try:
                if callable(progress_callback):
                    progress_callback(1.0, "Conversation generated")
            except Exception as e:
                print(f"Progress callback error: {e}")  # Log but continue

            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

# Remove the legacy agent definition completely 