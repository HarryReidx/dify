# Enhanced Document Processing Plugin

A comprehensive plugin for Dify that extends document processing capabilities with multi-format support, image handling, and intelligent segmentation.

## Features

- **Multi-format Document Support**: Convert doc, docx, xls, xlsx, ppt, pptx, and image files to PDF
- **Enhanced MinerU Integration**: Extended MinerU plugin with format conversion capabilities
- **Image Processing**: Extract images from documents and store in MinIO with public URLs
- **Parent-Child Segmentation**: Intelligent document segmentation based on hierarchical structure
- **Large Document Upload**: Bypass HTTP parameter limits using file upload API
- **Exam Generation**: Generate test questions from knowledge base content

## Installation

1. Install dependencies:
```bash
cd api/plugins/enhanced_document_processing
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Choose and install document conversion tools (optional, based on your needs):

**Option A: LibreOffice (Recommended - Best compatibility)**
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# CentOS/RHEL
sudo yum install libreoffice

# macOS
brew install --cask libreoffice

# Windows: Download from https://www.libreoffice.org/
```

**Option B: Pandoc (Lightweight alternative)**
```bash
# Ubuntu/Debian
sudo apt-get install pandoc wkhtmltopdf

# macOS
brew install pandoc wkhtmltopdf

# Windows: Download from https://pandoc.org/
```

**Option C: Pure Python (No external dependencies)**
- No additional installation needed
- Uses python-docx, openpyxl, python-pptx, reportlab
- Limited formatting support but works everywhere

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EDP_ENABLE_FORMAT_CONVERSION` | Enable document format conversion | `true` |
| `EDP_CONVERSION_ENGINE` | Conversion engine (`auto`, `libreoffice`, `pandoc`, `python_libs`) | `auto` |
| `EDP_ENABLE_IMAGE_PROCESSING` | Enable image extraction and processing | `true` |
| `EDP_MINIO_ENDPOINT` | MinIO server endpoint | Required if image processing enabled |
| `EDP_MINIO_ACCESS_KEY` | MinIO access key | Required if image processing enabled |
| `EDP_MINIO_SECRET_KEY` | MinIO secret key | Required if image processing enabled |
| `EDP_UPLOAD_METHOD` | Upload method (`auto`, `http_api`, `file_upload`) | `auto` |

See `.env.example` for complete configuration options.

### MinIO Setup

If image processing is enabled, you need a MinIO server:

1. Install MinIO:
```bash
# Using Docker
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

2. Create the bucket specified in `EDP_MINIO_BUCKET` (default: `dify-images`)

3. Set bucket policy to public read for image URLs to work

## Usage

### Basic Document Processing

```python
from api.plugins.enhanced_document_processing import EnhancedDocumentProcessingPlugin

# Initialize plugin
plugin = EnhancedDocumentProcessingPlugin()

# Process a document
result = plugin.process_document("/path/to/document.docx", "dataset_id")

if result.success:
    print(f"Processed successfully: {len(result.images)} images, {len(result.segments)} segments")
    print(f"Upload result: {result.metadata['upload_result']}")
else:
    print(f"Processing failed: {result.error_message}")
```

### Exam Generation

```python
# Generate exam from knowledge base
exam_config = {
    "question_count": 10,
    "question_types": ["multiple_choice", "short_answer"],
    "include_images": True
}

exam = plugin.generate_exam_from_dataset("dataset_id", exam_config)
print(f"Generated {len(exam['questions'])} questions")
```

### Custom Configuration

```python
from api.plugins.enhanced_document_processing import DocumentProcessingConfig

# Custom configuration
config = DocumentProcessingConfig(
    enable_format_conversion=True,
    enable_image_processing=False,  # Disable image processing
    max_segment_length=500,
    upload_method=UploadMethod.FILE_UPLOAD
)

plugin = EnhancedDocumentProcessingPlugin(config)
```

## Supported Formats

### Input Formats
- **Office Documents**: doc, docx, xls, xlsx, ppt, pptx
- **Images**: jpg, jpeg, png, gif, bmp, tiff, webp
- **Text**: txt, rtf, md
- **Other**: pdf (direct processing), odt

### Output Format
All documents are converted to PDF for unified processing through MinerU.

## Architecture

The plugin consists of several key components:

1. **DocumentConverter**: Handles format detection and conversion to PDF
2. **ImageProcessingService**: Extracts images and uploads to MinIO
3. **ParentChildSegmenter**: Creates hierarchical document segments
4. **DocumentUploadService**: Handles upload to Dify knowledge base
5. **ExamGenerationService**: Generates test questions from content

## Error Handling

The plugin includes comprehensive error handling:

- **UnsupportedFormatError**: File format not supported
- **ConversionFailedError**: Document conversion failed
- **ImageExtractionError**: Image extraction failed
- **MinIOUploadError**: MinIO upload failed
- **ContentTooLargeError**: Content exceeds size limits
- **ConfigurationError**: Invalid configuration

## Development

### Project Structure
```
api/plugins/enhanced_document_processing/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── models.py                # Data models
├── exceptions.py            # Custom exceptions
├── utils.py                 # Utility functions
├── converter.py             # Document conversion
├── image_processor.py       # Image processing
├── segmenter.py            # Document segmentation
├── uploader.py             # Document upload
├── exam_generator.py       # Exam generation
├── plugin.py               # Main plugin class
├── requirements.txt        # Dependencies
├── .env.example           # Configuration template
└── README.md              # This file
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v --cov=api/plugins/enhanced_document_processing
```

## Conversion Engines

### Auto Mode (Recommended)
When `EDP_CONVERSION_ENGINE=auto`, the plugin automatically selects the best available converter:

1. **LibreOffice** (Priority: 100) - Best compatibility, handles complex formatting
2. **Pandoc** (Priority: 75) - Good for text-based documents, lightweight
3. **Python Libraries** (Priority: 50) - Basic conversion, works everywhere

### Manual Selection
You can force a specific engine:
- `EDP_CONVERSION_ENGINE=libreoffice` - Use only LibreOffice
- `EDP_CONVERSION_ENGINE=pandoc` - Use only Pandoc  
- `EDP_CONVERSION_ENGINE=python_libs` - Use only Python libraries

## Troubleshooting

### Common Issues

1. **No converters available**: Install at least one conversion tool (LibreOffice, Pandoc, or ensure Python libraries are installed)
2. **MinIO connection failed**: Check MinIO server is running and credentials are correct
3. **Large document upload fails**: Try setting `EDP_UPLOAD_METHOD=file_upload`
4. **Image URLs not accessible**: Ensure MinIO bucket has public read policy

### Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('api.plugins.enhanced_document_processing').setLevel(logging.DEBUG)
```

## License

This plugin is part of the Dify project and follows the same license terms.

## API Reference

### Main Plugin Class

```python
from api.plugins.enhanced_document_processing import EnhancedDocumentProcessingPlugin

plugin = EnhancedDocumentProcessingPlugin()

# Process a document
result = plugin.process_document('/path/to/document.docx', 'dataset_id')

# Generate exam
exam_config = {
    'question_count': 10,
    'question_types': ['multiple_choice', 'short_answer'],
    'include_images': True
}
exam = plugin.generate_exam_from_dataset('dataset_id', exam_config)

# Enhance Q&A response
enhanced = plugin.enhance_qa_response(response_text, context_segments)

# Get plugin status
status = plugin.get_comprehensive_status()
```

### Configuration Options

```python
from api.plugins.enhanced_document_processing import DocumentProcessingConfig

config = DocumentProcessingConfig(
    # Format conversion
    enable_format_conversion=True,
    conversion_engine='auto',  # 'auto', 'libreoffice', 'pandoc', 'python_libs'
    
    # Image processing
    enable_image_processing=True,
    minio_endpoint='localhost:9000',
    minio_access_key='minioadmin',
    minio_secret_key='minioadmin',
    
    # Document segmentation
    enable_parent_child_segmentation=True,
    max_segment_length=1000,
    min_segment_length=100,
    
    # Upload settings
    upload_method='auto',  # 'auto', 'http_api', 'file_upload'
    
    # Exam generation
    enable_exam_generation=True
)
```

## Performance Optimization

### Memory Usage
- Large documents are processed in chunks to minimize memory usage
- Temporary files are automatically cleaned up
- Image processing uses streaming where possible

### Processing Speed
- LibreOffice provides fastest conversion for Office documents
- Parent-child segmentation is optimized for large documents
- Concurrent image processing for multiple images

### Scalability
- Supports batch processing of multiple documents
- MinIO provides scalable image storage
- Configurable retry mechanisms for reliability

## Monitoring and Logging

### Enable Debug Logging
```python
import logging
logging.getLogger('api.plugins.enhanced_document_processing').setLevel(logging.DEBUG)
```

### Performance Monitoring
```python
# Run performance test
perf_stats = plugin.run_performance_test('/path/to/test/document.pdf')
print(f"Processing time: {perf_stats['processing_time']:.2f}s")
print(f"Memory used: {perf_stats['memory_used_mb']:.1f}MB")
```

### Health Checks
```python
# Get comprehensive status
status = plugin.get_comprehensive_status()
print(f"System ready: {status['configuration_status']['valid']}")
```

## Deployment

### Production Deployment
1. Install with all dependencies: `pip install -r requirements.txt`
2. Install LibreOffice for best conversion support
3. Set up MinIO server for image storage
4. Configure environment variables
5. Test with sample documents

### Docker Deployment
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Test installation
python3 -c "from plugin import EnhancedDocumentProcessingPlugin; print('Plugin loaded successfully')"
```

### Kubernetes Deployment
- Use persistent volumes for temporary file storage
- Configure MinIO as a separate service
- Set resource limits based on document sizes
- Use horizontal pod autoscaling for high loads

## Best Practices

### Document Processing
- Use LibreOffice for complex Office documents
- Enable parent-child segmentation for structured documents
- Configure appropriate segment sizes for your use case
- Test with representative document samples

### Image Handling
- Set up MinIO with appropriate storage policies
- Configure image quality based on your needs
- Monitor MinIO storage usage
- Use CDN for high-traffic scenarios

### Error Handling
- Enable retry mechanisms for production
- Monitor error rates and types
- Set up alerting for critical failures
- Keep logs for troubleshooting

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all configuration is environment-variable based
5. Test with multiple document types and sizes
6. Consider performance impact of changes
