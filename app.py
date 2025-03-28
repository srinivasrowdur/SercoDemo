import streamlit as st
import tempfile
import os
from pydub import AudioSegment
import io
import shutil
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import glob
from agents.orchestrator import Orchestrator

# Load environment variables from .env file
load_dotenv()

# Check if ffmpeg is installed
if not shutil.which('ffmpeg'):
    st.error("FFmpeg is not installed. Please install FFmpeg to use this app.")
    st.markdown("""
    Install FFmpeg:
    - Mac: `brew install ffmpeg`
    - Ubuntu/Debian: `sudo apt-get install ffmpeg`
    - Windows: Download from https://www.gyan.dev/ffmpeg/builds/
    """)
    st.stop()

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client with API key
client = OpenAI(api_key=api_key)

# Initialize orchestrator with OpenAI client
orchestrator = Orchestrator(client)

def update_progress(progress_bar, progress, status=""):
    progress_bar.progress(progress, text=status)

def convert_to_wav(audio_bytes):
    try:
        # Read directly from bytes
        audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        audio = audio.set_frame_rate(16000).set_channels(1)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        return wav_io.read()
    except Exception as e:
        st.error(f"Error converting audio: {str(e)}")
        return None

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

def transcribe_audio(audio_bytes, progress_bar):
    try:
        # Convert input audio to AudioSegment
        audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        update_progress(progress_bar, 0.1, "Converting audio...")
        
        # Convert to mono and set sample rate to reduce file size
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Split into chunks
        chunks = split_audio(audio)
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
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    full_transcription.append(transcription)
            except Exception as chunk_error:
                st.error(f"Error processing chunk {i+1}: {str(chunk_error)}")
                continue
            finally:
                # Clean up temporary file
                os.remove(temp_file_path)
            
            # Update progress (allocate 70% of the progress bar to transcription)
            progress = 0.1 + (0.7 * (i + 1) / total_chunks)
            update_progress(progress_bar, progress, f"Transcribing audio... ({i+1}/{total_chunks})")
        
        if not full_transcription:
            st.error("No chunks were successfully transcribed")
            return None
            
        # Combine all transcriptions
        final_transcription = " ".join(full_transcription)
        return final_transcription
        
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

def convert_to_conversation(text, progress_bar):
    try:
        message_placeholder = st.empty()
        full_response = ""
        
        update_progress(progress_bar, 0.8, "Generating conversation...")
        
        # Create streaming response
        stream = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": """
                You are an expert medical transcriptionist with years of experience in documenting clinical conversations. 
                Your task is to convert the following text into a precise dialogue format, ensuring:
                
                1. Maintain absolute accuracy of medical terminology and dosages
                2. Preserve all clinical details, no matter how minor they might seem
                3. Keep exact numbers, measurements, and timelines as mentioned
                4. Retain all mentions of:
                   - Symptoms and their duration
                   - Medications and their dosages
                   - Treatment plans and schedules
                   - Patient concerns and doctor's responses
                   - Follow-up instructions
                   - Side effects or adverse reactions discussed
                   - Lifestyle recommendations
                
                Format the conversation as a natural dialogue with clear speaker labels and line breaks between speakers.
                Do not summarize or omit any details - every word could be clinically significant.
                """},
                {"role": "user", "content": text}
            ],
            stream=True
        )
        
        # Process the streaming response
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        
        # Display final response
        message_placeholder.markdown(full_response)
        update_progress(progress_bar, 0.9, "Conversation generated")
        return full_response
    except Exception as e:
        st.error(f"Error converting to conversation: {str(e)}")
        return None

def extract_medical_info(text, progress_bar):
    try:
        message_placeholder = st.empty()
        full_response = ""
        
        update_progress(progress_bar, 0.9, "Generating medical summary...")
        
        # Create streaming response
        stream = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": """
                You are a medical documentation specialist. Extract and organize the following information from the conversation in a detailed, structured format:

                1. Medications:
                   - Name of each medication
                   - Dosage prescribed
                   - Frequency of administration
                   - Duration of treatment
                   - Route of administration

                2. Treatment Plan:
                   - Prescribed treatments/procedures
                   - Treatment schedule
                   - Treatment duration
                   - Special instructions

                3. Side Effects:
                   - Reported side effects
                   - Potential side effects discussed
                   - Warnings given

                4. Effectiveness:
                   - Reported effectiveness of current/previous treatments
                   - Expected outcomes
                   - Follow-up requirements

                5. Important Notes:
                   - Any specific warnings
                   - Contraindications
                   - Drug interactions
                   - Lifestyle modifications

                Format the information clearly with headers and bullet points. If any information is not mentioned in the conversation, indicate 'Not discussed' for that section.
                Only include information that was explicitly mentioned in the conversation - do not make assumptions or add information not present in the transcript.
                """},
                {"role": "user", "content": text}
            ],
            stream=True  # Enable streaming
        )
        
        # Process the streaming response without displaying intermediate results
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
        
        # Format the markdown properly
        # Ensure headers have space after # and lists have proper spacing
        formatted_response = ""
        for line in full_response.split('\n'):
            # Fix headers (ensure space after #)
            if line.startswith('#') and not line.startswith('# '):
                line = line.replace('#', '# ', 1)
            
            # Fix nested lists (ensure proper indentation)
            if line.strip().startswith('-') or line.strip().startswith('*'):
                if line.strip() != line:  # It's indented
                    # Make sure indentation is consistent (use 4 spaces)
                    indent_level = len(line) - len(line.lstrip())
                    line = ' ' * indent_level + '- ' + line.strip()[1:].strip()
                else:
                    line = '- ' + line.strip()[1:].strip()
            
            formatted_response += line + '\n'
        
        # Only display the final response once at the end
        update_progress(progress_bar, 1.0, "Complete!")
        message_placeholder.markdown(formatted_response)
        return formatted_response
    except Exception as e:
        st.error(f"Error extracting medical information: {str(e)}")
        return None

def save_uploaded_file(uploaded_file):
    """Save uploaded file to audio folder with timestamp"""
    # Create audio directory if it doesn't exist
    audio_dir = "audio"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    
    # Get file extension
    file_extension = os.path.splitext(uploaded_file.name)[1]
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_filename = os.path.splitext(uploaded_file.name)[0]
    new_filename = f"{original_filename}_{timestamp}{file_extension}"
    
    # Full path for saving
    file_path = os.path.join(audio_dir, new_filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    return file_path

def list_audio_files():
    """List all audio files in the audio directory"""
    if not os.path.exists("audio"):
        return []
    return sorted(glob.glob("audio/*.mp3"), key=os.path.getmtime, reverse=True)

def format_filename(filepath):
    """Format filename for display"""
    filename = os.path.basename(filepath)
    name, _ = os.path.splitext(filename)
    # Split by underscore and remove timestamp
    parts = name.split('_')[:-2]  # Assuming format: name_YYYYMMDD_HHMMSS
    return ' '.join(parts).title()

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

def get_or_create_session_state():
    if 'file_just_uploaded' not in st.session_state:
        st.session_state.file_just_uploaded = False
    if 'selected_audio' not in st.session_state:
        st.session_state.selected_audio = None
    if 'current_summary' not in st.session_state:
        st.session_state.current_summary = None
    # Clear summaries when switching files
    if 'last_file' not in st.session_state:
        st.session_state.last_file = None

def save_transcription(transcription, original_filename, timestamp):
    """Save transcription to transcriptions folder"""
    # Create transcriptions directory if it doesn't exist
    transcriptions_dir = "transcriptions"
    if not os.path.exists(transcriptions_dir):
        os.makedirs(transcriptions_dir)
    
    # Create filename with just the date (not time)
    date_only = timestamp.split('_')[0]  # Get YYYYMMDD part
    new_filename = f"{original_filename}_{date_only}.md"
    file_path = os.path.join(transcriptions_dir, new_filename)
    
    # Save the transcription with metadata
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(f"# Transcription: {original_filename}\n")
        f.write(f"Date: {datetime.strptime(date_only, '%Y%m%d').strftime('%B %d, %Y')}\n\n")
        f.write("## Content\n\n")
        f.write(transcription)
    
    return file_path

def save_conversation(conversation, original_filename, timestamp):
    """Save conversation to conversations folder"""
    # Create conversations directory if it doesn't exist
    conversations_dir = "conversations"
    if not os.path.exists(conversations_dir):
        os.makedirs(conversations_dir)
    
    # Create filename with just the date (not time)
    date_only = timestamp.split('_')[0]  # Get YYYYMMDD part
    new_filename = f"{original_filename}_{date_only}.md"
    file_path = os.path.join(conversations_dir, new_filename)
    
    # Save the conversation with metadata
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(f"# Conversation: {original_filename}\n")
        f.write(f"Date: {datetime.strptime(date_only, '%Y%m%d').strftime('%B %d, %Y')}\n\n")
        f.write("## Dialogue\n\n")
        f.write(conversation)
    
    return file_path

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

def load_markdown_file(filepath):
    """Load and return contents of a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None

def delete_recording(audio_file):
    """Delete recording and its associated files"""
    try:
        # Find associated files
        associated_files = find_associated_files(audio_file)
        
        # Delete audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        # Delete transcription if exists
        if associated_files['transcription'] and os.path.exists(associated_files['transcription']):
            os.remove(associated_files['transcription'])
            
        # Delete conversation if exists
        if associated_files['conversation'] and os.path.exists(associated_files['conversation']):
            os.remove(associated_files['conversation'])
            
        # Clean up session state
        if 'current_summary' in st.session_state:
            st.session_state.current_summary = None
        if 'last_file' in st.session_state:
            st.session_state.last_file = None
        if 'selected_audio' in st.session_state:
            st.session_state.selected_audio = None
            
        # Clear any summary keys for this file
        summary_key = f"summary_{audio_file}"
        if summary_key in st.session_state:
            del st.session_state[summary_key]
            
        return True
    except Exception as e:
        st.error(f"Error deleting files: {str(e)}")
        return False

def process_audio_file(audio_bytes, progress_bar, operation_type="transcription", use_existing_transcription=False, transcription_text=None):
    """Process audio file with progress updates"""
    # Create a proper progress callback function
    def make_progress_callback(base_progress=0, scale=1.0):
        def callback(progress, text):
            if progress_bar and hasattr(progress_bar, 'progress'):
                update_progress(progress_bar, base_progress + (progress * scale), text)
        return callback

    if operation_type == "transcription":
        return orchestrator.process_transcription(
            audio_bytes, 
            make_progress_callback(0, 1.0)
        )
    elif operation_type == "conversation":
        # Don't transcribe again if we already have the text
        if use_existing_transcription and transcription_text:
            return orchestrator.process_conversation(
                transcription_text,
                make_progress_callback(0.4, 0.6)
            )
        else:
            # Only transcribe if we don't have the text
            transcription_text = orchestrator.process_transcription(
                audio_bytes,
                make_progress_callback(0, 0.4)
            )
            if not transcription_text or transcription_text.startswith("Error"):
                return None

            return orchestrator.process_conversation(
                transcription_text,
                make_progress_callback(0.4, 0.6)
            )
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")

def main():
    get_or_create_session_state()
    
    # Set page title
    st.title("Report Generator Agent")

    # Sidebar setup
    st.sidebar.title("Audio Files")

    # File uploader
    uploaded_file = st.sidebar.file_uploader("Upload New MP3", type=["mp3"], 
                                           on_change=lambda: setattr(st.session_state, 'file_just_uploaded', True))

    # If a file was just uploaded, save it and rerun
    if st.session_state.file_just_uploaded:
        if uploaded_file is not None:
            # Save the uploaded file
            saved_file_path = save_uploaded_file(uploaded_file)
            st.session_state.file_just_uploaded = False  # Reset the flag
            st.rerun()  # Rerun the app to update the sidebar
        
    # Divider
    st.sidebar.markdown("---")

    # List existing files
    st.sidebar.subheader("Previous Recordings")
    
    # Get list of audio files
    audio_files = list_audio_files()
    
    # Display audio files with custom styling
    for audio_file in audio_files:
        with st.sidebar.container():
            # Custom CSS for the audio container
            st.markdown("""
            <style>
            .audio-container {
                background-color: #1E1E1E;
                border-radius: 10px;
                padding: 10px;
                margin: 10px 0;
            }
            .file-name {
                color: #FFFFFF;
                font-size: 16px;
                margin-bottom: 5px;
            }
            .file-date {
                color: #888888;
                font-size: 12px;
            }
            .waveform {
                background: linear-gradient(90deg, #4CAF50 0%, #2196F3 100%);
                height: 40px;
                border-radius: 5px;
                margin: 5px 0;
            }
            </style>
            """, unsafe_allow_html=True)

            # Create a custom container for each audio file
            st.markdown(f"""
            <div class="audio-container">
                <div class="file-name">{format_filename(audio_file)}</div>
                <div class="file-date">{get_file_date(audio_file)}</div>
                <div class="waveform"></div>
            </div>
            """, unsafe_allow_html=True)

            try:
                # Audio player with better error handling
                with open(audio_file, 'rb') as f:
                    audio_bytes = f.read()
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                    wav_io = io.BytesIO()
                    audio.export(wav_io, format='wav')
                    wav_io.seek(0)
                    
                    # Create two columns for the buttons
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Display audio player
                        st.audio(wav_io, format='audio/wav')
                        
                        # Check if files exist before showing the load button
                        associated_files = find_associated_files(audio_file)
                        has_files = associated_files['transcription'] is not None or associated_files['conversation'] is not None
                        
                        # Add a button to load the file content
                        button_label = f"Load {format_filename(audio_file)}"
                        if has_files:
                            if st.button(button_label, key=f"btn_{audio_file}"):
                                st.session_state.selected_audio = audio_file
                                st.rerun()
                        else:
                            # Disabled button with tooltip
                            st.button(
                                button_label, 
                                key=f"btn_{audio_file}", 
                                disabled=True,
                                help="No transcription or conversation available yet"
                            )
                    
                    with col2:
                        # Add delete button
                        if st.button("🗑️", key=f"del_{audio_file}", 
                                   help="Delete recording and associated files"):
                            if delete_recording(audio_file):
                                st.success("Recording deleted")
                                # Clear selected audio if it was the deleted one
                                if st.session_state.selected_audio == audio_file:
                                    st.session_state.selected_audio = None
                                st.rerun()

            except Exception as e:
                st.error(f"Unable to play audio file. Error: {str(e)}")

            # Add a subtle separator
            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    # Main content area
    if uploaded_file is not None:
        try:
            # Get the bytes once and reuse
            audio_bytes = uploaded_file.getvalue()
            
            # Get original filename and timestamp
            original_filename = os.path.splitext(uploaded_file.name)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create the file path that matches how it was saved in the sidebar
            saved_file_path = os.path.join("audio", f"{original_filename}_{timestamp}.mp3")
            
            # Create tabs
            tab1, tab2, tab3 = st.tabs(["Transcription", "Conversation", "Medical Summary"])
            
            # Check for existing files first
            associated_files = find_associated_files(saved_file_path)
            
            # Transcription tab
            with tab1:
                st.header("Transcription")
                if associated_files['transcription']:
                    content = load_markdown_file(associated_files['transcription'])
                    if content:
                        transcription = content.split("## Content\n\n")[-1]
                        # Store in orchestrator context
                        orchestrator.context['transcription'] = transcription
                    st.markdown(content)
                else:
                    # Only transcribe if no existing file
                    progress_bar = st.progress(0, text="Starting transcription...")
                    
                    def make_progress_callback(base_progress=0, scale=1.0):
                        def callback(progress, text):
                            if progress_bar and hasattr(progress_bar, 'progress'):
                                update_progress(progress_bar, base_progress + (progress * scale), text)
                        return callback
                    
                    # Use the progress callback
                    result = orchestrator.process_transcription(
                        audio_bytes, 
                        make_progress_callback(0, 1.0)
                    )
                    
                    if result:
                        if result.startswith("Error"):
                            st.error(result)  # Display the detailed error message
                        else:
                            transcription_path = save_transcription(result, original_filename, timestamp)
                            content = load_markdown_file(transcription_path)
                            if content:
                                transcription = content.split("## Content\n\n")[-1]
                                # Store in orchestrator context
                                orchestrator.context['transcription'] = transcription
                            st.markdown(content)
            
            # Conversation tab
            with tab2:
                st.header("Conversation")
                if associated_files['conversation']:
                    content = load_markdown_file(associated_files['conversation'])
                    if content:
                        st.markdown(content)
                else:
                    # Check if we have transcription in context
                    if 'transcription' not in orchestrator.context:
                        st.error("Please generate a transcription first")
                        return

                    progress_bar = st.progress(0, text="Starting...")
                    message_placeholder = st.empty()
                    
                    def streaming_callback(progress, text):
                        if text.endswith("▌"):
                            message_placeholder.markdown(text[:-1], unsafe_allow_html=True)
                        else:
                            update_progress(progress_bar, 0.4 + (progress * 0.6), text)
                    
                    # Use transcription from context
                    result = orchestrator.process_conversation(
                        orchestrator.context['transcription'],
                        streaming_callback
                    )
                    
                    if result and not result.startswith("Error"):
                        conversation_path = save_conversation(result, original_filename, timestamp)
                        message_placeholder.markdown(result)
                    else:
                        st.error(f"Failed to generate conversation: {result}")
                    
                    progress_bar.empty()
            
            # Medical Summary tab
            with tab3:
                st.header("Medical Summary")
                
                # Clear summary if we switched files
                current_file = audio_file  # or saved_file_path depending on context
                if st.session_state.last_file != current_file:
                    if 'current_summary' in st.session_state:
                        st.session_state.current_summary = None
                    st.session_state.last_file = current_file
                
                # Generate button
                if st.button("Generate Medical Summary", key=f"gen_summary_{current_file}"):
                    content = None
                    progress_bar = st.progress(0, text="Starting...")
                    
                    # Try to get conversation first, then transcription
                    if associated_files['conversation']:
                        content = load_markdown_file(associated_files['conversation'])
                        if content:
                            content = content.split("## Dialogue\n\n")[-1]
                    elif associated_files['transcription']:
                        content = load_markdown_file(associated_files['transcription'])
                        if content:
                            content = content.split("## Content\n\n")[-1]
                    
                    if content:
                        # Store the result in session state but don't display it again here
                        st.session_state.current_summary = extract_medical_info(content, progress_bar)
                    else:
                        st.error("No content available for summary generation")
                
                # Display current summary if available
                if st.session_state.current_summary:
                    # We don't need to render it again since extract_medical_info already did
                    st.download_button(
                        label="Download Summary",
                        data=st.session_state.current_summary,
                        file_name="medical_summary.txt",
                        mime="text/plain",
                        key=f"download_{current_file}"
                    )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    elif st.session_state.selected_audio is not None:
        try:
            audio_file = st.session_state.selected_audio
            
            # Create tabs
            tab1, tab2, tab3 = st.tabs(["Transcription", "Conversation", "Medical Summary"])
            
            # Find associated files
            associated_files = find_associated_files(audio_file)
            
            # Transcription tab
            with tab1:
                st.header("Transcription")
                if associated_files['transcription']:
                    content = load_markdown_file(associated_files['transcription'])
                    if content:
                        st.markdown(content)
                else:
                    st.info("No transcription available")
            
            # Conversation tab
            with tab2:
                st.header("Conversation")
                if associated_files['conversation']:
                    content = load_markdown_file(associated_files['conversation'])
                    if content:
                        st.markdown(content)
                else:
                    st.info("No conversation available")
            
            # Medical Summary tab
            with tab3:
                st.header("Medical Summary")
                
                # Store summary in session state to prevent regeneration
                summary_key = f"summary_{audio_file}"
                if summary_key not in st.session_state:
                    st.session_state[summary_key] = None
                
                # Generate button with unique key
                if st.button("Generate Medical Summary", key=f"gen_summary_{audio_file}"):
                    content = None
                    progress_bar = st.progress(0, text="Starting...")
                    
                    # Try to get conversation first, then transcription
                    if associated_files['conversation']:
                        content = load_markdown_file(associated_files['conversation'])
                        if content:
                            content = content.split("## Dialogue\n\n")[-1]
                    elif associated_files['transcription']:
                        content = load_markdown_file(associated_files['transcription'])
                        if content:
                            content = content.split("## Content\n\n")[-1]
                    
                    if content:
                        # Store the result in session state - extract_medical_info will display it once
                        st.session_state[summary_key] = extract_medical_info(content, progress_bar)
                
                # Display summary if available
                if st.session_state[summary_key]:
                    # We don't need to display the summary again since extract_medical_info already did
                    st.download_button(
                        label="Download Summary",
                        data=st.session_state[summary_key],
                        file_name="medical_summary.txt",
                        mime="text/plain",
                        key=f"download_{audio_file}"
                    )

        except Exception as e:
            st.error(f"Error loading file content: {str(e)}")
    else:
        st.write("Upload a recording to get started.")

if __name__ == "__main__":
    main()