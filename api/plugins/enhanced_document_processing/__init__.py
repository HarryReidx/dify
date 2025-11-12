"""
Enhanced Document Processing Plugin for Dify

This plugin extends Dify's document processing capabilities with:
- Multi-format document conversion (doc, docx, xls, xlsx, ppt, pptx, images)
- Enhanced MinerU integration
- Image extraction and MinIO storage
- Parent-child document segmentation
- Large document upload via file API
- Exam generation from knowledge base
"""

__version__ = "1.0.0"
__author__ = "Enhanced Document Processing Team"

from .config import DocumentProcessingConfig
from .converter import DocumentConverter
from .image_processor import ImageProcessingService
from .segmenter import ParentChildSegmenter
from .uploader import DocumentUploadService

__all__ = [
    "DocumentProcessingConfig",
    "DocumentConverter",
    "ImageProcessingService",
    "ParentChildSegmenter",
    "DocumentUploadService"
]
