from swarm import Agent

class MedicalSummaryAgent(Agent):
    def __init__(self, client):
        super().__init__(
            name="Medical Summary Agent",
            model="gpt-4",
            instructions="You are a medical summarization expert. Extract and organize key medical information.",
            functions=[self.generate_summary]
        )
        self.client = client
        
    def generate_summary(self, text):
        """Generate a medical summary from the conversation"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}" 