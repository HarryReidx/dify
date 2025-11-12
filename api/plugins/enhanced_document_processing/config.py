"""
Configuration management for Enhanced Document Processing Plugin
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class UploadMethod(Enum):
    """Upload method enumeration"""
    AUTO = "auto"
    HTTP_API = "http_api"
    FILE_UPLOAD = "file_upload"


@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing plugin"""

    # Format conversion settings
    enable_format_conversion: bool = True
    supported_formats: List[str] = field(default_factory=lambda: [
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'
    ])

    # Document conversion settings
    conversion_engine: str = "auto"  # auto, libreoffice, python_libs, pandoc
    libreoffice_path: str = "/usr/bin/libreoffice"
    conversion_timeout: int = 300  # seconds
    pandoc_path: str = "/usr/bin/pandoc"

    # Image processing settings
    enable_image_processing: bool = True
    image_quality: int = 85
    max_image_size: int = 5 * 1024 * 1024  # 5MB
    image_formats: List[str] = field(default_factory=lambda: [
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'
    ])

    # MinIO configuration
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "dify-images"
    minio_secure: bool = True
    minio_region: str = "us-east-1"

    # Document segmentation settings
    max_segment_length: int = 1000
    min_segment_length: int = 100
    overlap_length: int = 50
    enable_parent_child_segmentation: bool = True

    # Upload settings
    upload_method: UploadMethod = UploadMethod.AUTO
    http_api_size_limit: int = 1024 * 1024  # 1MB
    enable_upload_retry: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds

    # MinerU integration settings
    mineru_config_path: Optional[str] = None
    enable_mineru_enhancement: bool = True

    # Exam generation settings
    enable_exam_generation: bool = True
    default_question_count: int = 10
    supported_question_types: List[str] = field(default_factory=lambda: [
        'multiple_choice', 'fill_blank', 'short_answer', 'essay'
    ])

    @classmethod
    def from_env(cls) -> 'DocumentProcessingConfig':
        """Create configuration from environment variables"""
        return cls(
            # Format conversion
            enable_format_conversion=os.getenv('EDP_ENABLE_FORMAT_CONVERSION', 'true').lower() == 'true',
            conversion_engine=os.getenv('EDP_CONVERSION_ENGINE', 'auto'),
            libreoffice_path=os.getenv('EDP_LIBREOFFICE_PATH', '/usr/bin/libreoffice'),
            conversion_timeout=int(os.getenv('EDP_CONVERSION_TIMEOUT', '300')),
            pandoc_path=os.getenv('EDP_PANDOC_PATH', '/usr/bin/pandoc'),

            # Image processing
            enable_image_processing=os.getenv('EDP_ENABLE_IMAGE_PROCESSING', 'true').lower() == 'true',
            image_quality=int(os.getenv('EDP_IMAGE_QUALITY', '85')),
            max_image_size=int(os.getenv('EDP_MAX_IMAGE_SIZE', str(5 * 1024 * 1024))),

            # MinIO
            minio_endpoint=os.getenv('EDP_MINIO_ENDPOINT', ''),
            minio_access_key=os.getenv('EDP_MINIO_ACCESS_KEY', ''),
            minio_secret_key=os.getenv('EDP_MINIO_SECRET_KEY', ''),
            minio_bucket=os.getenv('EDP_MINIO_BUCKET', 'dify-images'),
            minio_secure=os.getenv('EDP_MINIO_SECURE', 'true').lower() == 'true',
            minio_region=os.getenv('EDP_MINIO_REGION', 'us-east-1'),

            # Segmentation
            max_segment_length=int(os.getenv('EDP_MAX_SEGMENT_LENGTH', '1000')),
            min_segment_length=int(os.getenv('EDP_MIN_SEGMENT_LENGTH', '100')),
            overlap_length=int(os.getenv('EDP_OVERLAP_LENGTH', '50')),
            enable_parent_child_segmentation=os.getenv('EDP_ENABLE_PARENT_CHILD_SEGMENTATION', 'true').lower() == 'true',

            # Upload
            upload_method=UploadMethod(os.getenv('EDP_UPLOAD_METHOD', 'auto')),
            http_api_size_limit=int(os.getenv('EDP_HTTP_API_SIZE_LIMIT', str(1024 * 1024))),
            enable_upload_retry=os.getenv('EDP_ENABLE_UPLOAD_RETRY', 'true').lower() == 'true',
            max_retry_attempts=int(os.getenv('EDP_MAX_RETRY_ATTEMPTS', '3')),
            retry_delay=float(os.getenv('EDP_RETRY_DELAY', '1.0')),

            # MinerU
            mineru_config_path=os.getenv('EDP_MINERU_CONFIG_PATH'),
            enable_mineru_enhancement=os.getenv('EDP_ENABLE_MINERU_ENHANCEMENT', 'true').lower() == 'true',

            # Exam generation
            enable_exam_generation=os.getenv('EDP_ENABLE_EXAM_GENERATION', 'true').lower() == 'true',
            default_question_count=int(os.getenv('EDP_DEFAULT_QUESTION_COUNT', '10')),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if self.enable_image_processing:
            if not self.minio_endpoint:
                errors.append("MinIO endpoint is required when image processing is enabled")
            if not self.minio_access_key:
                errors.append("MinIO access key is required when image processing is enabled")
            if not self.minio_secret_key:
                errors.append("MinIO secret key is required when image processing is enabled")

        if self.max_segment_length <= self.min_segment_length:
            errors.append("max_segment_length must be greater than min_segment_length")

        if self.overlap_length >= self.min_segment_length:
            errors.append("overlap_length must be less than min_segment_length")

        if self.image_quality < 1 or self.image_quality > 100:
            errors.append("image_quality must be between 1 and 100")

        if self.max_retry_attempts < 1:
            errors.append("max_retry_attempts must be at least 1")

        return errors

    def is_format_supported(self, file_extension: str) -> bool:
        """Check if file format is supported"""
        return file_extension.lower().lstrip('.') in self.supported_formats

    def is_image_format(self, file_extension: str) -> bool:
        """Check if file format is an image"""
        return file_extension.lower().lstrip('.') in self.image_formats
