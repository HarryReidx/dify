"""
Utility functions for Enhanced Document Processing Plugin
"""

import os
import mimetypes
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
import logging

from .exceptions import UnsupportedFormatError, ConfigurationError

logger = logging.getLogger(__name__)


def detect_file_format(file_path: str) -> Tuple[str, str]:
    """
    Detect file format from file path and content

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (extension, mime_type)

    Raises:
        UnsupportedFormatError: If format cannot be detected
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get extension from filename
    file_ext = Path(file_path).suffix.lower().lstrip('.')

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(file_path)

    # Try magic number detection for better accuracy
    try:
        import magic
        detected_mime = magic.from_file(file_path, mime=True)
        if detected_mime and detected_mime != 'application/octet-stream':
            mime_type = detected_mime
    except ImportError:
        # python-magic not available, continue with mimetypes
        pass
    except Exception:
        # Magic detection failed, continue with existing detection
        pass

    if not file_ext and not mime_type:
        raise UnsupportedFormatError(f"Cannot detect format for file: {file_path}")

    # Fallback to extension-based detection if MIME type is not available
    if not mime_type:
        mime_type = _get_mime_type_from_extension(file_ext)

    # Validate detected format
    if not _is_supported_format(file_ext, mime_type):
        raise UnsupportedFormatError(f"Unsupported format: {file_ext} ({mime_type})")

    return file_ext, mime_type or "application/octet-stream"


def _get_mime_type_from_extension(extension: str) -> Optional[str]:
    """Get MIME type from file extension"""
    mime_map = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'webp': 'image/webp',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'rtf': 'application/rtf',
        'odt': 'application/vnd.oasis.opendocument.text'
    }
    return mime_map.get(extension.lower())


def is_office_document(file_extension: str) -> bool:
    """Check if file is an Office document"""
    office_formats = {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt'}
    return file_extension.lower().lstrip('.') in office_formats


def is_image_file(file_extension: str) -> bool:
    """Check if file is an image"""
    image_formats = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}
    return file_extension.lower().lstrip('.') in image_formats


def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
    """
    Calculate hash of file content

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')

    Returns:
        Hex digest of file hash
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def create_temp_file(suffix: str = '', prefix: str = 'edp_', content: bytes = None) -> str:
    """
    Create a temporary file

    Args:
        suffix: File suffix/extension
        prefix: File prefix
        content: Optional content to write to file

    Returns:
        Path to created temporary file
    """
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)

    try:
        if content:
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
        else:
            os.close(fd)

        return temp_path
    except Exception:
        # Clean up on error
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def cleanup_temp_file(file_path: str) -> None:
    """Safely remove temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except OSError as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")


def ensure_directory(directory_path: str) -> None:
    """Ensure directory exists, create if necessary"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def validate_file_path(file_path: str) -> None:
    """
    Validate file path

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not readable
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"File is not readable: {file_path}")


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Remove or replace problematic characters
    import re

    # Replace spaces and special characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)

    # Ensure it's not too long
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255-len(ext)] + ext

    return safe_name


def extract_text_preview(text: str, max_length: int = 200) -> str:
    """
    Extract a preview of text content

    Args:
        text: Full text content
        max_length: Maximum length of preview

    Returns:
        Text preview
    """
    if len(text) <= max_length:
        return text

    # Try to break at word boundary
    preview = text[:max_length]
    last_space = preview.rfind(' ')

    if last_space > max_length * 0.8:  # If we can break at a reasonable point
        preview = preview[:last_space]

    return preview + "..."


def _is_supported_format(file_ext: str, mime_type: str) -> bool:
    """Check if the detected format is supported"""
    supported_extensions = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp',
        'txt', 'md', 'rtf', 'odt', 'ods', 'odp'
    }

    supported_mimes = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp',
        'text/plain', 'text/markdown', 'application/rtf',
        'application/vnd.oasis.opendocument.text',
        'application/vnd.oasis.opendocument.spreadsheet',
        'application/vnd.oasis.opendocument.presentation'
    }

    return file_ext.lower() in supported_extensions or mime_type in supported_mimes


def create_format_detector():
    """Create a format detector with enhanced capabilities"""
    class FormatDetector:
        def __init__(self):
            self.supported_formats = {
                'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp',
                'pdf', 'txt', 'md', 'rtf', 'odt', 'ods', 'odp'
            }

        def detect(self, file_path: str) -> dict:
            """Detect file format and return detailed information"""
            file_ext, mime_type = detect_file_format(file_path)
            file_size = get_file_size(file_path)

            return {
                'extension': file_ext,
                'mime_type': mime_type,
                'size': file_size,
                'size_formatted': format_file_size(file_size),
                'is_office_document': is_office_document(file_ext),
                'is_image': is_image_file(file_ext),
                'is_supported': file_ext in self.supported_formats
            }

        def is_supported(self, file_path: str) -> bool:
            """Check if file format is supported"""
            try:
                file_ext, _ = detect_file_format(file_path)
                return file_ext in self.supported_formats
            except Exception:
                return False

    return FormatDetector()


def merge_dictionaries(*dicts) -> dict:
    """
    Merge multiple dictionaries, with later ones taking precedence

    Args:
        *dicts: Dictionaries to merge

    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def retry_on_exception(max_attempts: int = 3, delay: float = 1.0,
                      exceptions: Tuple = (Exception,)):
    """
    Decorator for retrying function calls on exceptions

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed. Last error: {e}")

            raise last_exception

        return wrapper
    return decorator
