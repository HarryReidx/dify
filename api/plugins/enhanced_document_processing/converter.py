"""
Document format converter for Enhanced Document Processing Plugin
"""

import os
import logging
from typing import List, Optional

from .config import DocumentProcessingConfig
from .models import ConversionResult
from .exceptions import UnsupportedFormatError, ConversionFailedError
from .utils import detect_file_format
from .converters import LibreOfficeConverter, PythonLibsConverter, PandocConverter

logger = logging.getLogger(__name__)


class DocumentConverter:
    """Main document converter that delegates to specific converters"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config
        self.converters = []
        self._register_converters()

    def _register_converters(self):
        """Register available converters based on configuration and availability"""
        potential_converters = []

        # Prioritize LibreOffice as requested
        if self.config.conversion_engine in ['auto', 'libreoffice']:
            potential_converters.append(LibreOfficeConverter(self.config))

        if self.config.conversion_engine in ['auto', 'pandoc']:
            potential_converters.append(PandocConverter(self.config))

        if self.config.conversion_engine in ['auto', 'python_libs']:
            potential_converters.append(PythonLibsConverter(self.config))

        # Filter to only available converters and sort by priority
        available_converters = [c for c in potential_converters if c.is_available()]
        self.converters = sorted(available_converters, key=lambda x: x.get_priority(), reverse=True)

        if not self.converters:
            logger.warning("No document converters are available!")
            # Add fallback Python converter even if not fully available
            self.converters.append(PythonLibsConverter(self.config))
        else:
            converter_names = [type(c).__name__ for c in self.converters]
            logger.info(f"Available converters (by priority): {converter_names}")

    def get_conversion_progress(self, file_path: str) -> dict:
        """Get conversion progress information"""
        return {
            'status': 'ready',
            'supported_formats': self.get_supported_formats(),
            'preferred_converter': type(self.converters[0]).__name__ if self.converters else 'None',
            'file_info': self._get_file_info(file_path) if os.path.exists(file_path) else None
        }

    def _get_file_info(self, file_path: str) -> dict:
        """Get detailed file information"""
        from .utils import create_format_detector
        detector = create_format_detector()
        return detector.detect(file_path)

    def detect_format(self, file_path: str) -> str:
        """
        Detect document format

        Args:
            file_path: Path to the document

        Returns:
            File extension/format

        Raises:
            UnsupportedFormatError: If format is not supported
        """
        try:
            file_ext, mime_type = detect_file_format(file_path)
            logger.debug(f"Detected format: {file_ext} (MIME: {mime_type})")
            return file_ext
        except Exception as e:
            raise UnsupportedFormatError(f"Cannot detect format for {file_path}: {e}")

    def convert_to_pdf(self, file_path: str, output_path: str) -> ConversionResult:
        """
        Convert document to PDF format

        Args:
            file_path: Path to input document
            output_path: Path for output PDF

        Returns:
            ConversionResult with conversion details

        Raises:
            UnsupportedFormatError: If format is not supported
            ConversionFailedError: If conversion fails
        """
        if not os.path.exists(file_path):
            raise ConversionFailedError(f"Input file not found: {file_path}")

        # Detect format
        file_ext = self.detect_format(file_path)

        # If already PDF, just copy
        if file_ext.lower() == 'pdf':
            import shutil
            shutil.copy2(file_path, output_path)
            return ConversionResult(
                success=True,
                input_path=file_path,
                output_path=output_path,
                original_format='pdf',
                file_size=os.path.getsize(output_path),
                conversion_time=0.0
            )

        # Find suitable converter
        suitable_converters = [c for c in self.converters if c.can_convert(file_ext)]

        if not suitable_converters:
            available_formats = set()
            for converter in self.converters:
                available_formats.update(converter.get_supported_formats())

            raise UnsupportedFormatError(
                f"No converter available for format '{file_ext}'. "
                f"Supported formats: {sorted(available_formats)}"
            )

        # Try converters in priority order
        last_error = None
        for converter in suitable_converters:
            try:
                logger.info(f"Attempting conversion with {type(converter).__name__}")
                result = converter.convert(file_path, output_path)

                if result.success:
                    logger.info(f"Conversion successful using {type(converter).__name__}")
                    return result
                else:
                    logger.warning(f"Conversion failed with {type(converter).__name__}: {result.error_message}")
                    last_error = result.error_message

            except Exception as e:
                logger.warning(f"Converter {type(converter).__name__} threw exception: {e}")
                last_error = str(e)
                continue

        # All converters failed
        raise ConversionFailedError(f"All converters failed. Last error: {last_error}")

    def supports_format(self, format: str) -> bool:
        """
        Check if format is supported for conversion

        Args:
            format: File format/extension

        Returns:
            True if format is supported
        """
        format_clean = format.lower().lstrip('.')

        # Check if any converter supports this format
        for converter in self.converters:
            if converter.can_convert(format_clean):
                return True

        return False

    def get_supported_formats(self) -> List[str]:
        """Get list of all supported formats from all converters"""
        supported = set()
        for converter in self.converters:
            supported.update(converter.get_supported_formats())
        return sorted(supported)

    def get_converter_info(self) -> dict:
        """Get information about available converters"""
        info = {
            'conversion_engine': self.config.conversion_engine,
            'available_converters': [],
            'supported_formats': self.get_supported_formats()
        }

        for converter in self.converters:
            info['available_converters'].append({
                'name': type(converter).__name__,
                'priority': converter.get_priority(),
                'supported_formats': converter.get_supported_formats(),
                'available': converter.is_available()
            })

        return info
