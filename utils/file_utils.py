import os
import glob
from datetime import datetime

class FileUtils:
    @staticmethod
    def save_uploaded_file(uploaded_file, directory="audio"):
        """Save uploaded file to specified folder with timestamp"""
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Get file extension
        file_extension = os.path.splitext(uploaded_file.name)[1]
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = os.path.splitext(uploaded_file.name)[0]
        new_filename = f"{original_filename}_{timestamp}{file_extension}"
        
        # Full path for saving
        file_path = os.path.join(directory, new_filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        return file_path

    @staticmethod
    def list_audio_files(directory="audio"):
        """List all audio files in the specified directory"""
        if not os.path.exists(directory):
            return []
        return sorted(glob.glob(f"{directory}/*.mp3"), key=os.path.getmtime, reverse=True)

    @staticmethod
    def format_filename(filepath):
        """Format filename for display"""
        filename = os.path.basename(filepath)
        name, _ = os.path.splitext(filename)
        # Split by underscore and remove timestamp
        parts = name.split('_')[:-2]  # Assuming format: name_YYYYMMDD_HHMMSS
        return ' '.join(parts).title()

    @staticmethod
    def get_file_date(filepath):
        """Get formatted date from filename"""
        filename = os.path.basename(filepath)
        timestamp = filename.split('_')[-2:]  # Get YYYYMMDD_HHMMSS
        if len(timestamp) >= 2:
            datetime_str = f"{timestamp[0]}_{timestamp[1]}"
            try:
                file_date = datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")
                return file_date.strftime("%b %d, %Y %I:%M %p")
            except:
                return "Date unknown"
        return "Date unknown"

    @staticmethod
    def save_markdown_file(content, directory, original_filename, timestamp, prefix=""):
        """Save content to markdown file with metadata"""
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Create filename with just the date (not time)
        date_only = timestamp.split('_')[0]  # Get YYYYMMDD part
        new_filename = f"{original_filename}_{date_only}.md"
        file_path = os.path.join(directory, new_filename)
        
        # Save the content with metadata
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(f"# {prefix}: {original_filename}\n")
            f.write(f"Date: {datetime.strptime(date_only, '%Y%m%d').strftime('%B %d, %Y')}\n\n")
            f.write("## Content\n\n")
            f.write(content)
        
        return file_path

    @staticmethod
    def load_markdown_file(filepath):
        """Load and return contents of a markdown file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def find_associated_files(audio_filename):
        """Find associated transcription and conversation files"""
        # Get the original filename without the timestamp
        filename = os.path.basename(audio_filename)
        original_name = filename.split('_')[0]  # Get the part before first underscore
        
        # Get just the date from the audio filename
        date_only = filename.split('_')[-2]  # Get YYYYMMDD part
        
        # Create the base filename that matches our saved files
        base_filename = f"{original_name}_{date_only}"
        
        # Look for matching files with .md extension
        transcription_path = os.path.join("transcriptions", f"{base_filename}.md")
        conversation_path = os.path.join("conversations", f"{base_filename}.md")
        
        # Check if files exist
        trans_exists = os.path.exists(transcription_path)
        conv_exists = os.path.exists(conversation_path)
        
        return {
            'transcription': transcription_path if trans_exists else None,
            'conversation': conversation_path if conv_exists else None
        }

    @staticmethod
    def delete_files(main_file, associated_files):
        """Delete main file and its associated files"""
        try:
            # Delete main file
            if os.path.exists(main_file):
                os.remove(main_file)
                
            # Delete associated files
            for file_path in associated_files.values():
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    
            return True
        except Exception:
            return False