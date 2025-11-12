"""
Main plugin entry point for Enhanced Document Processing Plugin
"""

import logging
from typing import Dict, Any, Optional

from .config import DocumentProcessingConfig
from .converter import DocumentConverter
from .image_processor import ImageProcessingService
from .segmenter import ParentChildSegmenter
from .uploader import DocumentUploadService
from .exam_generator import ExamGenerationService
from .models import ProcessResult
from .exceptions import DocumentProcessingError, ConfigurationError

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessingPlugin:
    """Main plugin class that orchestrates document processing"""

    def __init__(self, config: Optional[DocumentProcessingConfig] = None):
        """
        Initialize the plugin

        Args:
            config: Plugin configuration, defaults to environment-based config
        """
        self.config = config or DocumentProcessingConfig.from_env()

        # Validate configuration
        config_errors = self.config.validate()
        if config_errors:
            raise ConfigurationError(f"Configuration errors: {', '.join(config_errors)}")

        # Initialize services
        self.converter = DocumentConverter(self.config)
        self.image_processor = ImageProcessingService(self.config)
        self.segmenter = ParentChildSegmenter(self.config)
        self.uploader = DocumentUploadService(self.config)
        self.exam_generator = ExamGenerationService(self.config)

        logger.info("Enhanced Document Processing Plugin initialized")

    def process_document(self, file_path: str, dataset_id: str) -> ProcessResult:
        """
        Process a document through the complete pipeline

        Args:
            file_path: Path to the document to process
            dataset_id: Target Dify dataset ID

        Returns:
            Processing result

        Raises:
            DocumentProcessingError: If processing fails
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Starting document processing for: {file_path}")

            # Step 1: Convert document to PDF if needed
            if not file_path.lower().endswith('.pdf'):
                if not self.config.enable_format_conversion:
                    raise DocumentProcessingError("Format conversion is disabled but non-PDF file provided")

                logger.info("Converting document to PDF...")
                conversion_result = self.converter.convert_to_pdf(file_path, file_path + '.pdf')
                if not conversion_result.success:
                    raise DocumentProcessingError(f"Document conversion failed: {conversion_result.error_message}")
                pdf_path = conversion_result.output_path
            else:
                pdf_path = file_path

            # Step 2: Extract markdown using MinerU (will be enhanced in task 3)
            logger.info("Extracting markdown content...")
            markdown_content = self._extract_markdown_with_mineru(pdf_path)

            # Step 3: Process images
            logger.info("Processing images...")
            images, updated_markdown = self.image_processor.process_document_images(pdf_path, markdown_content)

            # Step 4: Create segments
            logger.info("Creating document segments...")
            segments = self.segmenter.create_segments(updated_markdown)

            # Step 5: Upload to Dify
            logger.info("Uploading to Dify knowledge base...")
            upload_result = self.uploader.upload_document(updated_markdown, dataset_id)

            processing_time = time.time() - start_time

            result = ProcessResult(
                success=True,
                original_file_path=file_path,
                converted_file_path=pdf_path if pdf_path != file_path else None,
                markdown_content=updated_markdown,
                images=images,
                segments=segments,
                processing_time=processing_time,
                metadata={
                    'upload_result': upload_result,
                    'image_count': len(images),
                    'segment_count': len(segments)
                }
            )

            logger.info(f"Document processing completed successfully in {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Document processing failed after {processing_time:.2f}s: {e}")

            return ProcessResult(
                success=False,
                original_file_path=file_path,
                error_message=str(e),
                processing_time=processing_time
            )

    def _extract_markdown_with_mineru(self, pdf_path: str) -> str:
        """
        Extract markdown using enhanced MinerU integration

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted markdown content
        """
        try:
            from .mineru_integration import EnhancedMinerUProcessor

            processor = EnhancedMinerUProcessor(self.config)
            result = processor.process_pdf_with_mineru(pdf_path)

            # Enhance markdown structure
            enhanced_markdown = processor.enhance_markdown_structure(result['markdown_content'])

            logger.info(f"MinerU processing completed: {result['metadata']}")
            return enhanced_markdown

        except Exception as e:
            logger.warning(f"MinerU processing failed: {e}, using fallback")
            return self._fallback_text_extraction(pdf_path)

    def _fallback_text_extraction(self, pdf_path: str) -> str:
        """Fallback text extraction when MinerU fails"""
        try:
            import pypdfium2

            text_content = []
            with open(pdf_path, 'rb') as file:
                pdf = pypdfium2.PdfDocument(file)
                for page_num in range(len(pdf)):
                    page = pdf[page_num]
                    text_page = page.get_textpage()
                    text = text_page.get_text_range()
                    text_content.append(f"## Page {page_num + 1}\n\n{text}\n")
                    text_page.close()
                    page.close()
                pdf.close()

            return "\n".join(text_content)

        except Exception as e:
            logger.error(f"Fallback text extraction failed: {e}")
            return f"# Document Content\n\nFailed to extract content from: {pdf_path}"

    def generate_exam_from_dataset(self, dataset_id: str, exam_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate exam from knowledge base dataset

        Args:
            dataset_id: Dataset ID
            exam_config: Exam configuration

        Returns:
            Generated exam data
        """
        from .models import ExamConfig

        config = ExamConfig(**exam_config)
        result = self.exam_generator.generate_exam(dataset_id, config)

        return result.export_to_dict()

    def enhance_qa_response(self, response_text: str, context_segments: List[Dict]) -> Dict[str, Any]:
        """
        Enhance Q&A response with image display

        Args:
            response_text: Original response text
            context_segments: Context segments used for response

        Returns:
            Enhanced response with image information
        """
        try:
            from .qa_enhancer import QAEnhancementService

            qa_enhancer = QAEnhancementService(self.config)
            return qa_enhancer.enhance_qa_response(response_text, context_segments)

        except Exception as e:
            logger.error(f"Q&A enhancement failed: {e}")
            return {
                'enhanced_text': response_text,
                'original_text': response_text,
                'images': [],
                'image_count': 0,
                'valid_image_count': 0,
                'error': str(e)
            }

    def run_performance_test(self, test_file_path: str) -> Dict[str, Any]:
        """
        Run performance test on a document

        Args:
            test_file_path: Path to test document

        Returns:
            Performance metrics
        """
        import time
        import psutil
        import os

        # Get initial system stats
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        initial_cpu = process.cpu_percent()

        start_time = time.time()

        try:
            # Process document
            result = self.process_document(test_file_path, "test_dataset")

            end_time = time.time()

            # Get final system stats
            final_memory = process.memory_info().rss
            final_cpu = process.cpu_percent()

            return {
                'success': result.success,
                'processing_time': end_time - start_time,
                'memory_used': final_memory - initial_memory,
                'memory_used_mb': (final_memory - initial_memory) / 1024 / 1024,
                'cpu_usage': final_cpu - initial_cpu,
                'file_size': os.path.getsize(test_file_path),
                'images_processed': len(result.images),
                'segments_created': len(result.segments),
                'markdown_length': len(result.markdown_content),
                'error': result.error_message if not result.success else None
            }

        except Exception as e:
            return {
                'success': False,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive plugin status and diagnostics"""
        status = {
            'plugin_info': self.get_plugin_info(),
            'converter_info': self.converter.get_converter_info(),
            'image_processing_stats': self.image_processor.get_processing_stats(),
            'upload_stats': self.uploader.get_upload_stats(),
            'exam_generation_stats': self.exam_generator.get_generation_stats()
        }

        # Add system diagnostics
        try:
            from .deployment import DeploymentManager
            deployment_manager = DeploymentManager()
            status['system_requirements'] = deployment_manager.check_system_requirements()
            status['configuration_status'] = deployment_manager.validate_configuration()
        except Exception as e:
            status['diagnostics_error'] = str(e)

        return status

    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin information and status"""
        return {
            "name": "Enhanced Document Processing",
            "version": "1.0.0",
            "description": "Advanced document processing with multi-format support, image handling, and exam generation",
            "config": {
                "format_conversion_enabled": self.config.enable_format_conversion,
                "conversion_engine": self.config.conversion_engine,
                "image_processing_enabled": self.config.enable_image_processing,
                "parent_child_segmentation_enabled": self.config.enable_parent_child_segmentation,
                "exam_generation_enabled": self.config.enable_exam_generation,
                "supported_formats": self.config.supported_formats,
                "upload_method": self.config.upload_method.value,
                "mineru_enhancement_enabled": self.config.enable_mineru_enhancement
            },
            "status": "initialized",
            "features": [
                "Multi-format document conversion",
                "Enhanced MinerU integration",
                "Image extraction and MinIO storage",
                "Parent-child document segmentation",
                "Large document upload via file API",
                "Q&A response enhancement with images",
                "Exam generation from knowledge base"
            ]
        }
