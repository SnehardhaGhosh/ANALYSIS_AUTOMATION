import os
import sys
import logging

def setup_logging():
    """
    Centralized logging configuration for both Web App (Flask) and Terminal Scripts.
    Ensures:
    1. Consistent formatting across console and file logs.
    2. Real-time log flushing.
    3. Solves Windows file locking issues in Flask reloader parent process.
    4. Safe duplicate prevention.
    """
    root_logger = logging.getLogger()
    
    # Avoid duplicate initialization
    if getattr(root_logger, '_custom_handlers_set', False):
        return root_logger

    # 1. Resolve logs directory path safely
    try:
        from config import Config
        logs_folder = getattr(Config, "LOGS_FOLDER", "logs")
    except ImportError:
        logs_folder = "logs"
        
    logs_dir = os.path.abspath(logs_folder)
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, 'app.log')

    # 2. Determine if we are in the Flask reloader parent process
    # The parent process should NOT open the log file to avoid locking it on Windows
    is_flask_parent = False
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        main_script = os.path.basename(sys.argv[0]) if sys.argv else ""
        if main_script in ("app.py", "wsgi.py") or os.environ.get("FLASK_APP") is not None:
            is_flask_parent = True

    # Reconfigure sys.stdout and sys.stderr to UTF-8 on Windows if possible to support checkmarks and other Unicode
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    # 3. Create Handlers
    handlers = []

    # A. Safe Console Stream Handler (Avoids UnicodeEncodeError on older/unconfigured Windows consoles)
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                super().emit(record)
            except Exception:
                try:
                    msg = self.format(record)
                    safe_msg = msg.encode('ascii', errors='backslashreplace').decode('ascii')
                    self.stream.write(safe_msg + self.terminator)
                    self.flush()
                except Exception:
                    self.handleError(record)

    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    )
    handlers.append(console_handler)

    # B. File Handler (Only added if NOT the Flask reloader parent process to prevent locking)
    if not is_flask_parent:
        class FlushingFileHandler(logging.FileHandler):
            def emit(self, record):
                super().emit(record)
                self.flush()  # Flush after each write for real-time updates

        file_handler = FlushingFileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
        )
        handlers.append(file_handler)

    # 4. Configure Root Logger
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to prevent duplicate logging
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    for handler in handlers:
        root_logger.addHandler(handler)

    # 5. Configure Werkzeug (Flask Request Logger)
    # Direct it to our configured root logger handlers by enabling propagation
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = True
    # Remove werkzeug's own handlers to avoid duplicate output to console
    for handler in list(werkzeug_logger.handlers):
        werkzeug_logger.removeHandler(handler)

    # Mark as configured
    root_logger._custom_handlers_set = True
    
    if is_flask_parent:
        logging.info("Logging initialized for Flask Reloader (Console only, file deferred to worker)")
    else:
        logging.info(f"Logging initialized successfully. Logs written to {log_file}")
        
    return root_logger
