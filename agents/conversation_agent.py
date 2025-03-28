import time
from google import genai

class ConversationAgent:
    def __init__(self, client):
        self.client = client

    def generate_conversation(self, text, progress_callback, context=None):
        """Convert transcription to conversation format with streaming"""
        try:
            if not text:
                return "Error: No transcription text provided"

            # Use context if provided
            context = context or {}
            
            # Initial progress update
            if callable(progress_callback):
                progress_callback(0.2, "Generating conversation...")

            # System prompt for the model
            system_prompt = """You are an expert medical transcriptionist with a critical responsibility to preserve medical records with 100% accuracy. Your task is to convert the text into a precise dialogue format with these strict requirements:

1. CRITICAL: Every single word from the original transcription MUST be included - no omissions allowed

2. Speaker Identification:
   - Use EXACTLY the same speaker names/identifiers as they appear in the transcript
   - DO NOT change, standardize, or relabel any speakers
   - If a speaker is identified by name, use that exact name
   - Keep speaker labels exactly as mentioned, even if they change during the conversation

3. Medical Accuracy:
   - Preserve all medical terms exactly as spoken
   - Maintain all numbers, measurements, and dosages with perfect accuracy
   - Keep all dates, times, and durations exactly as mentioned
   - Include all mentioned symptoms, no matter how minor they seem

4. Conversation Structure:
   - Format as "[exact speaker name/identifier]: [exact words]"
   - Add a blank line between each speaker's dialogue
   - Start each new speaker's turn on a new line
   - Maintain the exact sequence of the conversation
   - Keep all filler words, hesitations, and interruptions
   - Preserve all overlapping speech or simultaneous talking

5. Content Preservation:
   - Include all mentioned medications with exact names and dosages
   - Preserve all treatment plans and instructions
   - Keep all patient concerns and complaints
   - Maintain all references to past medical history
   - Include all lifestyle recommendations
   - Preserve all follow-up instructions

6. Formatting Requirements:
   - Add one empty line between each dialogue turn
   - Use double line breaks between different speakers
   - Keep consecutive turns by the same speaker separated by a single line
   - Maintain clear visual separation between different parts of the conversation

7. Absolute Requirements:
   - NO summarizing or paraphrasing
   - NO omitting any details
   - NO changing any words
   - NO cleaning up or "improving" the language
   - NO rearranging the order of information
   - NO standardizing speaker labels

Remember: This is a legal medical record - every word and speaker identification must be preserved exactly as in the original transcript."""

            # Generate streaming response with the new API
            response = self.client.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=["System instructions: " + system_prompt, text]
            )
            
            # Process the stream
            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    # Update UI with streaming content
                    if callable(progress_callback):
                        progress_callback(0.6, full_response + "▌")
                        # Add a small delay to allow Streamlit to update
                        time.sleep(0.01)

            # Final progress update
            if callable(progress_callback):
                progress_callback(1.0, "Conversation generated")

            # Store result in context
            context['conversation'] = full_response

            return full_response

        except Exception as e:
            return f"Error: {str(e)}"

# Remove the legacy agent definition completely 