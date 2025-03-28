class MedicalSummaryAgent:
    def __init__(self, client):
        self.client = client
        self.name = "Medical Summary Agent"
        self.model = "gpt-4"
        self.instructions = "You are a medical summarization expert. Extract and organize key medical information."
        
    def generate_summary(self, text):
        """Generate a medical summary from the conversation"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}" 