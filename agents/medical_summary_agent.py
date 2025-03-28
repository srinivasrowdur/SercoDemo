from google import genai

class MedicalSummaryAgent:
    def __init__(self, client):
        self.client = client
        self.instructions = "You are a medical summarization expert. Extract and organize key medical information."
        
    def generate_summary(self, text):
        """Generate a medical summary from the conversation"""
        try:
            # Generate streaming response with the new API
            response = self.client.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=["System instructions: " + self.instructions, text]
            )
            return response.text
        except Exception as e:
            return f"Error generating summary: {str(e)}" 