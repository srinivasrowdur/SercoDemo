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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Convert the following text into a natural dialogue between the speakers identified by the speaker labels with line breaks between speakers."},
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
            model="gpt-4",
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
        
        # Process the streaming response
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                message_placeholder.markdown(full_response + "▌")
        
        # Display final response
        message_placeholder.markdown(full_response)
        update_progress(progress_bar, 1.0, "Complete!")
        return full_response
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

def main():
    get_or_create_session_state()
    
    # Set page title
    st.title("Audio Transcription App")

    # Sidebar for file upload
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
                    # Create an AudioSegment to verify the file
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                    # Convert to WAV format for better compatibility
                    wav_io = io.BytesIO()
                    audio.export(wav_io, format='wav')
                    wav_io.seek(0)
                    st.audio(wav_io, format='audio/wav')
            except Exception as e:
                st.error(f"Unable to play audio file. Error: {str(e)}")

            # Add a subtle separator
            st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    # Main content area
    if uploaded_file is not None:
        try:
            # Get the bytes once and reuse
            audio_bytes = uploaded_file.getvalue()
            
            # Get audio duration
            audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            duration_minutes = len(audio)/1000/60
            
            # Display duration in a sleek format
            col1, col2 = st.columns([3, 1])
            with col2:
                st.caption(f"🎵 Duration: {duration_minutes:.1f} min")
            
            # Create single progress bar above tabs
            progress_bar = st.progress(0, text="Starting...")
            
            # Create tabs
            tab1, tab2, tab3 = st.tabs(["Transcription", "Conversation", "Medical Summary"])
            
            # Process audio using the bytes we already have
            transcription = transcribe_audio(audio_bytes, progress_bar)
            
            if transcription:
                # Transcription tab
                with tab1:
                    st.header("Transcription")
                    st.write(transcription)
                
                # Conversation tab
                with tab2:
                    st.header("Conversation")
                    conversation = convert_to_conversation(transcription, progress_bar)
                
                # Medical Summary tab
                with tab3:
                    st.header("Medical Summary")
                    if st.button("Generate Medical Summary"):
                        medical_info = extract_medical_info(conversation if conversation else transcription, progress_bar)
                        if medical_info:
                            st.download_button(
                                label="Download Summary",
                                data=medical_info,
                                file_name="medical_summary.txt",
                                mime="text/plain"
                            )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    else:
        st.write("Upload an MP3 file to get started.")

if __name__ == "__main__":
    main()