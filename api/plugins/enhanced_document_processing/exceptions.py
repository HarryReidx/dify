"""
Custom exceptions for Enhanced Document Processing Plugin
"""


class DocumentProcessingError(Exception):
    """Base exception for document processing errors"""
    pass


class UnsupportedFormatError(DocumentProcessingError):
    """Raised when document format is not supported"""
    pass


class ConversionFailedError(DocumentProcessingError):
    """Raised when document conversion fails"""
    pass


class ImageExtractionError(DocumentProcessingError):
    """Raised when image extraction fails"""
    pass


class MinIOUploadError(DocumentProcessingError):
    """Raised when MinIO upload fails"""
    pass


class URLGenerationError(DocumentProcessingError):
    """Raised when URL generation fails"""
    pass


class ContentTooLargeError(DocumentProcessingError):
    """Raised when content exceeds size limits"""
    pass


class APIUploadError(DocumentProcessingError):
    """Raised when API upload fails"""
    pass


class FileUploadError(DocumentProcessingError):
    """Raised when file upload fails"""
    pass


class SegmentationError(DocumentProcessingError):
    """Raised when document segmentation fails"""
    pass


class ConfigurationError(DocumentProcessingError):
    """Raised when configuration is invalid"""
    pass


class ExamGenerationError(DocumentProcessingError):
    """Raised when exam generation fails"""
    pass
