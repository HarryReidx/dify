"""
Image processing service for Enhanced Document Processing Plugin
"""

import os
import re
import uuid
import logging
from typing import List, Dict, Optional, Tuple
from io import BytesIO
import time

from .config import DocumentProcessingConfig
from .models import ImageInfo, ProcessResult
from .exceptions import ImageExtractionError, MinIOUploadError, URLGenerationError
from .utils import retry_on_exception

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """Service for extracting, processing and storing images"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config
        self.minio_client = None
        self._initialize_minio()

    def _initialize_minio(self):
        """Initialize MinIO client"""
        if not self.config.enable_image_processing:
            return

        try:
            from minio import Minio
            from minio.error import S3Error

            # Create MinIO client
            self.minio_client = Minio(
                self.config.minio_endpoint,
                access_key=self.config.minio_access_key,
                secret_key=self.config.minio_secret_key,
                secure=self.config.minio_secure
            )

            # Ensure bucket exists
            if not self.minio_client.bucket_exists(self.config.minio_bucket):
                self.minio_client.make_bucket(
                    self.config.minio_bucket,
                    location=self.config.minio_region
                )
                logger.info(f"Created MinIO bucket: {self.config.minio_bucket}")

            # Set bucket policy for public read access
            self._set_bucket_policy()

            logger.info("MinIO client initialized successfully")

        except ImportError:
            logger.error("MinIO library not available. Install with: pip install minio")
            self.minio_client = None
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            self.minio_client = None

    def _set_bucket_policy(self):
        """Set bucket policy for public read access"""
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.config.minio_bucket}/*"]
                    }
                ]
            }

            import json
            self.minio_client.set_bucket_policy(
                self.config.minio_bucket,
                json.dumps(policy)
            )
            logger.debug("Set bucket policy for public read access")

        except Exception as e:
            logger.warning(f"Failed to set bucket policy: {e}")

    def extract_images_from_pdf(self, pdf_path: str) -> List[ImageInfo]:
        """
        Extract images from PDF document

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of extracted image information

        Raises:
            ImageExtractionError: If extraction fails
        """
        if not self.config.enable_image_processing:
            return []

        try:
            images = []

            # Try multiple extraction methods
            try:
                # Method 1: Use pypdfium2 for image extraction
                images.extend(self._extract_with_pypdfium2(pdf_path))
            except Exception as e:
                logger.warning(f"pypdfium2 extraction failed: {e}")

            if not images:
                try:
                    # Method 2: Use pdf2image as fallback
                    images.extend(self._extract_with_pdf2image(pdf_path))
                except Exception as e:
                    logger.warning(f"pdf2image extraction failed: {e}")

            if not images:
                try:
                    # Method 3: Use PyMuPDF as last resort
                    images.extend(self._extract_with_pymupdf(pdf_path))
                except Exception as e:
                    logger.warning(f"PyMuPDF extraction failed: {e}")

            logger.info(f"Extracted {len(images)} images from PDF")
            return images

        except Exception as e:
            raise ImageExtractionError(f"Failed to extract images from PDF: {e}")

    def _extract_with_pypdfium2(self, pdf_path: str) -> List[ImageInfo]:
        """Extract images using pypdfium2"""
        import pypdfium2
        from PIL import Image

        images = []

        with open(pdf_path, 'rb') as file:
            pdf = pypdfium2.PdfDocument(file)

            for page_num in range(len(pdf)):
                page = pdf[page_num]

                # Render page as image
                bitmap = page.render(scale=2.0)  # Higher resolution
                pil_image = bitmap.to_pil()

                # Convert to bytes
                img_buffer = BytesIO()
                pil_image.save(img_buffer, format='PNG', quality=self.config.image_quality)
                img_data = img_buffer.getvalue()

                if len(img_data) > 1000:  # Skip very small images
                    image_info = ImageInfo(
                        original_path=f"page_{page_num + 1}.png",
                        extracted_data=img_data,
                        mime_type='image/png',
                        size=len(img_data),
                        width=pil_image.width,
                        height=pil_image.height,
                        page_number=page_num + 1
                    )
                    images.append(image_info)

                page.close()

            pdf.close()

        return images

    def _extract_with_pdf2image(self, pdf_path: str) -> List[ImageInfo]:
        """Extract images using pdf2image"""
        try:
            from pdf2image import convert_from_path
            from PIL import Image

            images = []

            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, dpi=200)

            for page_num, page_image in enumerate(pages, 1):
                # Convert to bytes
                img_buffer = BytesIO()
                page_image.save(img_buffer, format='PNG', quality=self.config.image_quality)
                img_data = img_buffer.getvalue()

                image_info = ImageInfo(
                    original_path=f"page_{page_num}.png",
                    extracted_data=img_data,
                    mime_type='image/png',
                    size=len(img_data),
                    width=page_image.width,
                    height=page_image.height,
                    page_number=page_num
                )
                images.append(image_info)

            return images

        except ImportError:
            raise ImageExtractionError("pdf2image not available. Install with: pip install pdf2image")

    def _extract_with_pymupdf(self, pdf_path: str) -> List[ImageInfo]:
        """Extract images using PyMuPDF"""
        try:
            import fitz  # PyMuPDF

            images = []
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")

                        image_info = ImageInfo(
                            original_path=f"page_{page_num + 1}_img_{img_index}.png",
                            extracted_data=img_data,
                            mime_type='image/png',
                            size=len(img_data),
                            width=pix.width,
                            height=pix.height,
                            page_number=page_num + 1
                        )
                        images.append(image_info)

                    pix = None

            doc.close()
            return images

        except ImportError:
            raise ImageExtractionError("PyMuPDF not available. Install with: pip install PyMuPDF")

    @retry_on_exception(max_attempts=3, delay=1.0, exceptions=(MinIOUploadError,))
    def upload_image_to_minio(self, image_data: bytes, filename: str) -> str:
        """
        Upload image to MinIO storage

        Args:
            image_data: Image binary data
            filename: Target filename

        Returns:
            MinIO object key

        Raises:
            MinIOUploadError: If upload fails
        """
        if not self.minio_client:
            raise MinIOUploadError("MinIO client not initialized")

        try:
            # Generate unique object key
            file_ext = os.path.splitext(filename)[1] or '.png'
            object_key = f"images/{uuid.uuid4()}{file_ext}"

            # Upload to MinIO
            self.minio_client.put_object(
                self.config.minio_bucket,
                object_key,
                BytesIO(image_data),
                len(image_data),
                content_type=self._get_content_type(file_ext)
            )

            logger.debug(f"Uploaded image to MinIO: {object_key}")
            return object_key

        except Exception as e:
            raise MinIOUploadError(f"Failed to upload image to MinIO: {e}")

    def _get_content_type(self, file_ext: str) -> str:
        """Get content type for file extension"""
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.webp': 'image/webp'
        }
        return content_types.get(file_ext.lower(), 'image/png')

    def generate_public_url(self, object_key: str) -> str:
        """
        Generate public URL for MinIO object

        Args:
            object_key: MinIO object key

        Returns:
            Public URL

        Raises:
            URLGenerationError: If URL generation fails
        """
        try:
            if not self.minio_client:
                raise URLGenerationError("MinIO client not initialized")

            # Generate public URL
            protocol = "https" if self.config.minio_secure else "http"
            url = f"{protocol}://{self.config.minio_endpoint}/{self.config.minio_bucket}/{object_key}"

            return url

        except Exception as e:
            raise URLGenerationError(f"Failed to generate public URL: {e}")

    def replace_image_references(self, markdown: str, image_map: Dict[str, str]) -> str:
        """
        Replace image references in markdown with URLs

        Args:
            markdown: Original markdown content
            image_map: Mapping of original references to URLs

        Returns:
            Updated markdown with image URLs
        """
        if not image_map:
            return markdown

        updated_markdown = markdown

        # Replace image references
        for original_ref, url in image_map.items():
            # Replace various markdown image formats
            patterns = [
                rf'!\[([^\]]*)\]\({re.escape(original_ref)}\)',  # ![alt](ref)
                rf'!\[\]\({re.escape(original_ref)}\)',  # ![](ref)
                rf'<img[^>]*src=["\']?{re.escape(original_ref)}["\']?[^>]*>',  # HTML img tags
            ]

            for pattern in patterns:
                updated_markdown = re.sub(
                    pattern,
                    f'![Image]({url})',
                    updated_markdown,
                    flags=re.IGNORECASE
                )

        return updated_markdown

    def process_document_images(self, pdf_path: str, markdown_content: str) -> Tuple[List[ImageInfo], str]:
        """
        Complete image processing workflow

        Args:
            pdf_path: Path to PDF file
            markdown_content: Original markdown content

        Returns:
            Tuple of (image_list, updated_markdown)
        """
        if not self.config.enable_image_processing:
            logger.info("Image processing is disabled")
            return [], markdown_content

        try:
            # Step 1: Extract images from PDF
            logger.info("Extracting images from PDF...")
            images = self.extract_images_from_pdf(pdf_path)

            if not images:
                logger.info("No images found in PDF")
                return [], markdown_content

            # Step 2: Upload images to MinIO and generate URLs
            logger.info(f"Uploading {len(images)} images to MinIO...")
            image_map = {}
            processed_images = []

            for image in images:
                try:
                    # Upload image
                    object_key = self.upload_image_to_minio(
                        image.extracted_data,
                        image.original_path
                    )

                    # Generate public URL
                    public_url = self.generate_public_url(object_key)

                    # Update image info
                    image.minio_key = object_key
                    image.public_url = public_url
                    processed_images.append(image)

                    # Add to replacement map
                    image_map[image.original_path] = public_url

                    logger.debug(f"Processed image: {image.original_path} -> {public_url}")

                except Exception as e:
                    logger.warning(f"Failed to process image {image.original_path}: {e}")
                    continue

            # Step 3: Replace image references in markdown
            logger.info("Updating markdown with image URLs...")
            updated_markdown = self.replace_image_references(markdown_content, image_map)

            # Add image references at the end of each page if not already present
            updated_markdown = self._add_missing_image_references(
                updated_markdown, processed_images
            )

            logger.info(f"Successfully processed {len(processed_images)} images")
            return processed_images, updated_markdown

        except Exception as e:
            logger.error(f"Image processing workflow failed: {e}")
            return [], markdown_content

    def _add_missing_image_references(self, markdown: str, images: List[ImageInfo]) -> str:
        """Add image references for images not already in markdown"""
        lines = markdown.split('\n')
        updated_lines = []
        current_page = None

        for line in lines:
            updated_lines.append(line)

            # Detect page headers
            if line.startswith('## Page '):
                try:
                    page_num = int(line.split('Page ')[1])
                    current_page = page_num

                    # Add images for this page
                    page_images = [img for img in images if img.page_number == page_num]
                    for img in page_images:
                        if img.public_url not in markdown:
                            updated_lines.append(f"\n![Image from page {page_num}]({img.public_url})\n")

                except (ValueError, IndexError):
                    continue

        return '\n'.join(updated_lines)

    def get_processing_stats(self) -> Dict[str, any]:
        """Get image processing statistics"""
        return {
            'enabled': self.config.enable_image_processing,
            'minio_configured': self.minio_client is not None,
            'minio_endpoint': self.config.minio_endpoint,
            'minio_bucket': self.config.minio_bucket,
            'image_quality': self.config.image_quality,
            'max_image_size': self.config.max_image_size
        }
