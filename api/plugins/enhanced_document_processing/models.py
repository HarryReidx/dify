"""
Data models for Enhanced Document Processing Plugin
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from datetime import datetime


class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionType(Enum):
    """Question type enumeration for exam generation"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


@dataclass
class ImageInfo:
    """Information about extracted images"""
    original_path: str
    extracted_data: bytes
    mime_type: str
    size: int
    width: int
    height: int
    minio_key: str = ""
    public_url: str = ""
    page_number: Optional[int] = None
    extraction_timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.minio_key:
            # Generate unique MinIO key
            file_ext = self.mime_type.split('/')[-1] if '/' in self.mime_type else 'jpg'
            self.minio_key = f"images/{uuid.uuid4()}.{file_ext}"


@dataclass
class DocumentSegment:
    """Document segment with hierarchical information"""
    id: str
    content: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    level: int = 0
    start_position: int = 0
    end_position: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class HierarchyNode:
    """Node in document hierarchy"""
    title: str
    level: int
    start_position: int
    end_position: int
    content: str = ""
    children: List['HierarchyNode'] = field(default_factory=list)
    parent: Optional['HierarchyNode'] = None


@dataclass
class ProcessResult:
    """Result of document processing"""
    success: bool
    original_file_path: str
    converted_file_path: Optional[str] = None
    markdown_content: str = ""
    images: List[ImageInfo] = field(default_factory=list)
    segments: List[DocumentSegment] = field(default_factory=list)
    error_message: Optional[str] = None
    processing_time: float = 0.0
    status: ProcessingStatus = ProcessingStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadResult:
    """Result of document upload to Dify"""
    success: bool
    document_id: Optional[str] = None
    dataset_id: Optional[str] = None
    upload_method: str = ""
    file_size: int = 0
    error_message: Optional[str] = None
    upload_time: float = 0.0
    retry_count: int = 0


@dataclass
class ConversionResult:
    """Result of document format conversion"""
    success: bool
    input_path: str
    output_path: str = ""
    original_format: str = ""
    target_format: str = "pdf"
    file_size: int = 0
    conversion_time: float = 0.0
    error_message: Optional[str] = None


@dataclass
class Question:
    """Exam question model"""
    id: str
    type: QuestionType
    question_text: str
    options: List[str] = field(default_factory=list)  # For multiple choice
    correct_answer: str = ""
    explanation: str = ""
    difficulty: str = "medium"  # easy, medium, hard
    topic: str = ""
    images: List[str] = field(default_factory=list)  # Image URLs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ExamConfig:
    """Configuration for exam generation"""
    question_count: int = 10
    question_types: List[QuestionType] = field(default_factory=lambda: [QuestionType.MULTIPLE_CHOICE])
    difficulty_distribution: Dict[str, float] = field(default_factory=lambda: {
        "easy": 0.3, "medium": 0.5, "hard": 0.2
    })
    include_images: bool = True
    topics: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate exam configuration"""
        errors = []

        if self.question_count <= 0:
            errors.append("question_count must be positive")

        if not self.question_types:
            errors.append("at least one question type must be specified")

        difficulty_sum = sum(self.difficulty_distribution.values())
        if abs(difficulty_sum - 1.0) > 0.01:
            errors.append("difficulty distribution must sum to 1.0")

        return errors


@dataclass
class ExamResult:
    """Result of exam generation"""
    success: bool
    exam_id: str
    questions: List[Question] = field(default_factory=list)
    config: Optional[ExamConfig] = None
    generation_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.exam_id:
            self.exam_id = str(uuid.uuid4())

    def export_to_dict(self) -> Dict[str, Any]:
        """Export exam to dictionary format"""
        return {
            "exam_id": self.exam_id,
            "questions": [
                {
                    "id": q.id,
                    "type": q.type.value,
                    "question": q.question_text,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty,
                    "topic": q.topic,
                    "images": q.images
                }
                for q in self.questions
            ],
            "metadata": self.metadata
        }
