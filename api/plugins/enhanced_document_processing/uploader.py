"""
Document upload service for Enhanced Document Processing Plugin
"""

import os
import time
import tempfile
import requests
from typing import Optional, Dict, Any
import logging

from .config import DocumentProcessingConfig, UploadMethod
from .models import UploadResult
from .exceptions import ContentTooLargeError, APIUploadError, FileUploadError
from .utils import retry_on_exception, create_temp_file, cleanup_temp_file, format_file_size

logger = logging.getLogger(__name__)


class DocumentUploadService:
    """Service for uploading documents to Dify knowledge base"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config
        self.dify_api_base = os.getenv('DIFY_API_BASE', 'http://localhost:5001')
        self.dify_api_key = os.getenv('DIFY_API_KEY', '')

    def determine_upload_method(self, content_size: int) -> UploadMethod:
        """
        Determine the best upload method based on content size

        Args:
            content_size: Size of content in bytes

        Returns:
            Recommended upload method
        """
        if self.config.upload_method != UploadMethod.AUTO:
            logger.info(f"Using configured upload method: {self.config.upload_method.value}")
            return self.config.upload_method

        if content_size <= self.config.http_api_size_limit:
            logger.info(f"Content size ({format_file_size(content_size)}) within HTTP API limit, using HTTP API")
            return UploadMethod.HTTP_API
        else:
            logger.info(f"Content size ({format_file_size(content_size)}) exceeds HTTP API limit, using file upload")
            return UploadMethod.FILE_UPLOAD

    @retry_on_exception(max_attempts=3, delay=1.0, exceptions=(APIUploadError,))
    def upload_via_api(self, content: str, dataset_id: str) -> UploadResult:
        """
        Upload document via HTTP API

        Args:
            content: Content to upload
            dataset_id: Target dataset ID

        Returns:
            Upload result

        Raises:
            APIUploadError: If API upload fails
        """
        start_time = time.time()
        content_size = len(content.encode('utf-8'))

        try:
            # Check size limit
            if content_size > self.config.http_api_size_limit:
                raise ContentTooLargeError(
                    f"Content size ({format_file_size(content_size)}) exceeds HTTP API limit "
                    f"({format_file_size(self.config.http_api_size_limit)})"
                )

            # Prepare API request
            url = f"{self.dify_api_base}/v1/datasets/{dataset_id}/documents"
            headers = {
                'Authorization': f'Bearer {self.dify_api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'name': f'processed_document_{int(time.time())}.md',
                'text': content,
                'indexing_technique': 'high_quality',
                'process_rule': {
                    'mode': 'custom',
                    'rules': {
                        'pre_processing_rules': [
                            {'id': 'remove_extra_spaces', 'enabled': True},
                            {'id': 'remove_urls_emails', 'enabled': False}
                        ],
                        'segmentation': {
                            'separator': '\n\n',
                            'max_tokens': self.config.max_segment_length
                        }
                    }
                }
            }

            logger.debug(f"Uploading via HTTP API to: {url}")

            # Make request
            response = requests.post(url, json=payload, headers=headers, timeout=60)

            if response.status_code == 200:
                result_data = response.json()
                upload_time = time.time() - start_time

                return UploadResult(
                    success=True,
                    document_id=result_data.get('document', {}).get('id'),
                    dataset_id=dataset_id,
                    upload_method='http_api',
                    file_size=content_size,
                    upload_time=upload_time
                )
            else:
                error_msg = f"HTTP API upload failed: {response.status_code} - {response.text}"
                raise APIUploadError(error_msg)

        except requests.exceptions.RequestException as e:
            raise APIUploadError(f"HTTP request failed: {e}")
        except Exception as e:
            if isinstance(e, (ContentTooLargeError, APIUploadError)):
                raise
            raise APIUploadError(f"Unexpected error during HTTP API upload: {e}")

    @retry_on_exception(max_attempts=3, delay=2.0, exceptions=(FileUploadError,))
    def upload_via_file(self, markdown_content: str, dataset_id: str) -> UploadResult:
        """
        Upload document via file API

        Args:
            markdown_content: Markdown content to upload
            dataset_id: Target dataset ID

        Returns:
            Upload result

        Raises:
            FileUploadError: If file upload fails
        """
        start_time = time.time()
        content_size = len(markdown_content.encode('utf-8'))
        temp_file_path = None

        try:
            # Create temporary markdown file
            temp_file_path = create_temp_file(
                suffix='.md',
                prefix='dify_upload_',
                content=markdown_content.encode('utf-8')
            )

            logger.debug(f"Created temporary file: {temp_file_path}")

            # Prepare file upload request
            url = f"{self.dify_api_base}/v1/datasets/{dataset_id}/documents"
            headers = {
                'Authorization': f'Bearer {self.dify_api_key}'
            }

            # Prepare multipart form data
            with open(temp_file_path, 'rb') as file:
                files = {
                    'file': (f'processed_document_{int(time.time())}.md', file, 'text/markdown')
                }

                data = {
                    'indexing_technique': 'high_quality',
                    'process_rule': self._get_process_rule_json()
                }

                logger.debug(f"Uploading file via API to: {url}")

                # Make request
                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=300  # Longer timeout for file uploads
                )

            if response.status_code == 200:
                result_data = response.json()
                upload_time = time.time() - start_time

                return UploadResult(
                    success=True,
                    document_id=result_data.get('document', {}).get('id'),
                    dataset_id=dataset_id,
                    upload_method='file_upload',
                    file_size=content_size,
                    upload_time=upload_time
                )
            else:
                error_msg = f"File upload failed: {response.status_code} - {response.text}"
                raise FileUploadError(error_msg)

        except requests.exceptions.RequestException as e:
            raise FileUploadError(f"File upload request failed: {e}")
        except Exception as e:
            if isinstance(e, FileUploadError):
                raise
            raise FileUploadError(f"Unexpected error during file upload: {e}")
        finally:
            # Clean up temporary file
            if temp_file_path:
                cleanup_temp_file(temp_file_path)

    def _get_process_rule_json(self) -> str:
        """Get processing rules as JSON string for file upload"""
        import json

        process_rule = {
            'mode': 'custom',
            'rules': {
                'pre_processing_rules': [
                    {'id': 'remove_extra_spaces', 'enabled': True},
                    {'id': 'remove_urls_emails', 'enabled': False}
                ],
                'segmentation': {
                    'separator': '\n\n',
                    'max_tokens': self.config.max_segment_length
                }
            }
        }

        return json.dumps(process_rule)

    def upload_document(self, markdown_content: str, dataset_id: str) -> UploadResult:
        """
        Upload document using the best method

        Args:
            markdown_content: Markdown content to upload
            dataset_id: Target dataset ID

        Returns:
            Upload result
        """
        content_size = len(markdown_content.encode('utf-8'))
        upload_method = self.determine_upload_method(content_size)

        logger.info(f"Uploading document ({format_file_size(content_size)}) using method: {upload_method.value}")

        retry_count = 0
        last_error = None

        for attempt in range(self.config.max_retry_attempts if self.config.enable_upload_retry else 1):
            try:
                if upload_method == UploadMethod.HTTP_API:
                    result = self.upload_via_api(markdown_content, dataset_id)
                else:
                    result = self.upload_via_file(markdown_content, dataset_id)

                result.retry_count = retry_count
                return result

            except Exception as e:
                last_error = e
                retry_count += 1

                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")

                # Try switching methods on failure if retry is enabled
                if (self.config.enable_upload_retry and
                    upload_method == UploadMethod.HTTP_API and
                    attempt < self.config.max_retry_attempts - 1):

                    logger.info("Switching to file upload method for retry")
                    upload_method = UploadMethod.FILE_UPLOAD

                # Wait before retry
                if attempt < self.config.max_retry_attempts - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))  # Exponential backoff

        # All attempts failed
        return UploadResult(
            success=False,
            dataset_id=dataset_id,
            upload_method=upload_method.value,
            file_size=content_size,
            error_message=f"Upload failed after {retry_count} attempts. Last error: {last_error}",
            retry_count=retry_count
        )

    def upload_with_segments(self, markdown_content: str, dataset_id: str,
                           segments: list) -> UploadResult:
        """
        Upload document with pre-computed segments

        Args:
            markdown_content: Markdown content
            dataset_id: Target dataset ID
            segments: Pre-computed document segments

        Returns:
            Upload result
        """
        # For now, upload the full content and let Dify handle segmentation
        # In the future, this could upload individual segments
        result = self.upload_document(markdown_content, dataset_id)

        if result.success:
            result.metadata = {
                'segments_provided': len(segments),
                'hierarchical_segments': sum(1 for s in segments if s.metadata.get('type') == 'hierarchical')
            }

        return result

    def get_upload_stats(self) -> Dict[str, Any]:
        """Get upload service statistics"""
        return {
            'api_base': self.dify_api_base,
            'api_configured': bool(self.dify_api_key),
            'upload_method': self.config.upload_method.value,
            'http_api_size_limit': self.config.http_api_size_limit,
            'http_api_size_limit_formatted': format_file_size(self.config.http_api_size_limit),
            'retry_enabled': self.config.enable_upload_retry,
            'max_retry_attempts': self.config.max_retry_attempts,
            'retry_delay': self.config.retry_delay
        }
