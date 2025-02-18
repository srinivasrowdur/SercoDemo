from typing import Optional, Dict, Any, Callable, List
import logging
import traceback
from datetime import datetime, timedelta
import time
from functools import wraps
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SercoError(Exception):
    """Base exception class for all Serco application errors"""
    def __init__(self, message: str, error_code: str, severity: str = "ERROR", context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)

class AudioProcessingError(SercoError):
    """Raised when there's an error processing audio files"""
    pass

class TranscriptionError(SercoError):
    """Raised when there's an error during transcription"""
    pass

class ConversationError(SercoError):
    """Raised when there's an error processing conversation"""
    pass

class APIError(SercoError):
    """Raised when there's an error with external API calls"""
    pass

class ErrorHandler:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.logger = logging.getLogger('serco_error_handler')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session_state = {}
        # Initialize error analytics storage
        self.error_metrics = {
            'frequency': defaultdict(int),  # Tracks error occurrence count by error_code
            'resolution_times': defaultdict(list),  # Tracks resolution times by error_code
            'patterns': defaultdict(list),  # Stores error patterns for analysis
            'last_occurrence': {},  # Tracks last occurrence of each error type
            'severity_counts': defaultdict(int)  # Tracks error counts by severity
        }

    def retry_on_failure(self, retryable_exceptions: tuple = (APIError, TranscriptionError)):
        """Decorator for implementing retry mechanism"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(self.max_retries):
                    try:
                        return func(*args, **kwargs)
                    except retryable_exceptions as e:
                        last_exception = e
                        if attempt < self.max_retries - 1:
                            self.logger.warning(
                                f"Attempt {attempt + 1} failed: {str(e)}. Retrying..."
                            )
                            time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                            continue
                raise last_exception
            return wrapper
        return decorator

    def preserve_session_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Store session state for recovery"""
        self.session_state[session_id] = state
        self.logger.info(f"Session state preserved for session {session_id}")

    def recover_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover session state if available"""
        state = self.session_state.get(session_id)
        if state:
            self.logger.info(f"Recovered session state for session {session_id}")
        return state

    def clear_session_state(self, session_id: str) -> None:
        """Clear preserved session state"""
        if session_id in self.session_state:
            del self.session_state[session_id]
            self.logger.info(f"Cleared session state for session {session_id}")


    def log_error(self, error: SercoError) -> None:
        """Log error with detailed context"""
        error_details = {
            'error_code': error.error_code,
            'message': error.message,
            'severity': error.severity,
            'timestamp': error.timestamp,
            'context': error.context,
            'traceback': traceback.format_exc()
        }
        
        self.logger.error(
            f"Error {error.error_code}: {error.message}",
            extra=error_details
        )

    def format_user_message(self, error: SercoError) -> str:
        """Format user-friendly error message"""
        base_message = f"Error: {error.message}"
        
        # Add suggested solutions based on error type
        solutions = {
            'AUDIO_FORMAT': "Please ensure the audio file is in MP3 format and not corrupted.",
            'TRANSCRIPTION': "Please try uploading the file again or check if the audio is clear.",
            'API_ERROR': "Please try again in a few moments. If the problem persists, contact support.",
            'CONVERSATION': "The system encountered an issue processing the conversation. Please try again."
        }
        
        if error.error_code in solutions:
            base_message += f"\n\nSuggestion: {solutions[error.error_code]}"
        
        return base_message

    def track_error(self, error: SercoError, resolution_time: Optional[float] = None) -> None:
        """Track error metrics for analytics"""
        error_code = error.error_code
        timestamp = error.timestamp

        # Update frequency metrics
        self.error_metrics['frequency'][error_code] += 1
        self.error_metrics['last_occurrence'][error_code] = timestamp
        self.error_metrics['severity_counts'][error.severity] += 1

        # Track resolution time if provided
        if resolution_time is not None:
            self.error_metrics['resolution_times'][error_code].append(resolution_time)

        # Store error pattern
        self.error_metrics['patterns'][error_code].append({
            'timestamp': timestamp,
            'context': error.context,
            'severity': error.severity
        })

    def get_error_analytics(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Generate error analytics report"""
        now = datetime.now()
        window_start = now - time_window if time_window else None

        analytics = {
            'total_errors': sum(self.error_metrics['frequency'].values()),
            'error_frequency': dict(self.error_metrics['frequency']),
            'severity_distribution': dict(self.error_metrics['severity_counts']),
            'average_resolution_times': {}
        }

        # Calculate average resolution times
        for error_code, times in self.error_metrics['resolution_times'].items():
            if times:
                analytics['average_resolution_times'][error_code] = sum(times) / len(times)

        # Identify error patterns
        analytics['error_patterns'] = self._analyze_error_patterns(window_start)

        return analytics

    def _analyze_error_patterns(self, window_start: Optional[datetime]) -> List[Dict[str, Any]]:
        """Analyze error patterns within the specified time window"""
        patterns = []
        for error_code, occurrences in self.error_metrics['patterns'].items():
            # Filter by time window if specified
            if window_start:
                occurrences = [o for o in occurrences if o['timestamp'] >= window_start]

            if occurrences:
                pattern = {
                    'error_code': error_code,
                    'occurrence_count': len(occurrences),
                    'severity_distribution': defaultdict(int),
                    'common_contexts': self._identify_common_contexts(occurrences)
                }

                # Calculate severity distribution
                for occurrence in occurrences:
                    pattern['severity_distribution'][occurrence['severity']] += 1

                patterns.append(pattern)

        return patterns

    def _identify_common_contexts(self, occurrences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common patterns in error contexts"""
        context_patterns = defaultdict(int)
        for occurrence in occurrences:
            context_key = str(sorted(occurrence['context'].items()))
            context_patterns[context_key] += 1

        # Return most common context patterns
        return [{
            'context': dict(eval(context_key)),
            'frequency': count
        } for context_key, count in sorted(
            context_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]]  # Return top 5 patterns

    def handle_error(self, error: Exception, session_id: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
        """Enhanced error handling with analytics tracking"""
        start_time = time.time()

        if session_id and isinstance(error, SercoError):
            self.preserve_session_state(session_id, {
                'last_error': {
                    'code': error.error_code,
                    'message': error.message,
                    'timestamp': error.timestamp.isoformat(),
                    'context': error.context
                }
            })

        if isinstance(error, SercoError):
            self.log_error(error)
            resolution_time = time.time() - start_time
            self.track_error(error, resolution_time)
            return self.format_user_message(error), {'error_code': error.error_code}

        unexpected_error = SercoError(
            message="An unexpected error occurred",
            error_code="UNEXPECTED",
            context={'original_error': str(error)}
        )
        self.log_error(unexpected_error)
        resolution_time = time.time() - start_time
        self.track_error(unexpected_error, resolution_time)
        return self.format_user_message(unexpected_error), {'error_code': 'UNEXPECTED'}