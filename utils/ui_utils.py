import streamlit as st

class UIUtils:
    @staticmethod
    def get_or_create_session_state():
        """Initialize or get session state variables"""
        if 'file_just_uploaded' not in st.session_state:
            st.session_state.file_just_uploaded = False
        if 'selected_audio' not in st.session_state:
            st.session_state.selected_audio = None
        if 'current_summary' not in st.session_state:
            st.session_state.current_summary = None
        if 'last_file' not in st.session_state:
            st.session_state.last_file = None

    @staticmethod
    def update_progress(progress_bar, progress, status=""):
        """Update progress bar with status"""
        if progress_bar and hasattr(progress_bar, 'progress'):
            progress_bar.progress(progress, text=status)

    @staticmethod
    def create_sidebar():
        """Create and configure the sidebar"""
        st.sidebar.image("serco.png", width=150)
        st.sidebar.title("Audio Files")

    @staticmethod
    def create_file_uploader(on_change=None):
        """Create file uploader widget"""
        return st.sidebar.file_uploader(
            "Upload New MP3",
            type=["mp3"],
            on_change=on_change
        )

    @staticmethod
    def create_audio_container(audio_file, format_filename_func, get_file_date_func,
                             on_transcribe, on_converse, on_delete):
        """Create a container for audio file display and controls"""
        with st.sidebar.container():
            st.markdown("""
            <style>
            .audio-container {
                background-color: #1E1E1E;
                border-radius: 10px;
                padding: 10px;
                margin: 10px 0;
            }
            </style>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(format_filename_func(audio_file))
                st.write(get_file_date_func(audio_file))
            with col2:
                st.button("🎯", key=f"transcribe_{audio_file}",
                         on_click=lambda: on_transcribe(audio_file))
                st.button("💬", key=f"converse_{audio_file}",
                         on_click=lambda: on_converse(audio_file))
                st.button("🗑", key=f"delete_{audio_file}",
                         on_click=lambda: on_delete(audio_file))

    @staticmethod
    def display_error(error_message):
        """Display error message"""
        st.error(error_message)

    @staticmethod
    def display_success(success_message):
        """Display success message"""
        st.success(success_message)

    @staticmethod
    def create_progress_bar():
        """Create a progress bar"""
        return st.progress(0)

    @staticmethod
    def create_tabs(tab_names):
        """Create tabs with given names"""
        return st.tabs(tab_names)

    @staticmethod
    def display_markdown(content):
        """Display markdown content"""
        st.markdown(content)