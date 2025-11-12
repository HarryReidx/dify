"""
Exam generation service for Enhanced Document Processing Plugin
"""

import re
import json
import time
import uuid
import random
from typing import List, Dict, Any, Optional
from io import BytesIO
import logging

from .config import DocumentProcessingConfig
from .models import Question, ExamConfig, ExamResult, QuestionType
from .exceptions import ExamGenerationError

logger = logging.getLogger(__name__)


class ExamGenerationService:
    """Service for generating exams from knowledge base content"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config

    def generate_exam(self, dataset_id: str, config: ExamConfig) -> ExamResult:
        """
        Generate exam from knowledge base

        Args:
            dataset_id: Knowledge base dataset ID
            config: Exam generation configuration

        Returns:
            Generated exam result

        Raises:
            ExamGenerationError: If exam generation fails
        """
        if not self.config.enable_exam_generation:
            raise ExamGenerationError("Exam generation is disabled")

        start_time = time.time()

        try:
            # Validate configuration
            config_errors = config.validate()
            if config_errors:
                raise ExamGenerationError(f"Invalid exam configuration: {', '.join(config_errors)}")

            # Retrieve content from knowledge base
            content_segments = self._retrieve_knowledge_base_content(dataset_id, config.topics)

            if not content_segments:
                raise ExamGenerationError(f"No content found in dataset {dataset_id}")

            # Generate questions
            questions = []
            questions_per_type = self._distribute_questions_by_type(config)

            for question_type, count in questions_per_type.items():
                type_questions = self._generate_questions_by_type(
                    content_segments, question_type, count, config
                )
                questions.extend(type_questions)

            # Apply difficulty distribution
            questions = self._apply_difficulty_distribution(questions, config.difficulty_distribution)

            # Shuffle questions
            random.shuffle(questions)

            # Limit to requested count
            questions = questions[:config.question_count]

            generation_time = time.time() - start_time

            return ExamResult(
                success=True,
                exam_id=str(uuid.uuid4()),
                questions=questions,
                config=config,
                generation_time=generation_time,
                metadata={
                    'dataset_id': dataset_id,
                    'content_segments_used': len(content_segments),
                    'questions_generated': len(questions),
                    'question_type_distribution': {qt.value: len([q for q in questions if q.type == qt])
                                                 for qt in config.question_types}
                }
            )

        except Exception as e:
            if isinstance(e, ExamGenerationError):
                raise

            return ExamResult(
                success=False,
                exam_id=str(uuid.uuid4()),
                config=config,
                generation_time=time.time() - start_time,
                error_message=str(e)
            )

    def _retrieve_knowledge_base_content(self, dataset_id: str, topics: List[str]) -> List[Dict[str, Any]]:
        """Retrieve content from knowledge base (mock implementation)"""
        # In a real implementation, this would query the Dify knowledge base
        # For now, return mock content
        mock_content = [
            {
                'id': 'segment_1',
                'content': 'Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.',
                'topic': 'machine_learning',
                'images': []
            },
            {
                'id': 'segment_2',
                'content': 'Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes.',
                'topic': 'neural_networks',
                'images': ['https://example.com/neural_network_diagram.png']
            },
            {
                'id': 'segment_3',
                'content': 'Deep learning uses neural networks with multiple hidden layers to model and understand complex patterns in data.',
                'topic': 'deep_learning',
                'images': []
            }
        ]

        # Filter by topics if specified
        if topics:
            mock_content = [seg for seg in mock_content if seg['topic'] in topics]

        return mock_content

    def _distribute_questions_by_type(self, config: ExamConfig) -> Dict[QuestionType, int]:
        """Distribute question count across question types"""
        total_questions = config.question_count
        question_types = config.question_types

        if not question_types:
            return {}

        # Equal distribution by default
        base_count = total_questions // len(question_types)
        remainder = total_questions % len(question_types)

        distribution = {}
        for i, question_type in enumerate(question_types):
            count = base_count + (1 if i < remainder else 0)
            distribution[question_type] = count

        return distribution

    def _generate_questions_by_type(self, content_segments: List[Dict],
                                   question_type: QuestionType, count: int,
                                   config: ExamConfig) -> List[Question]:
        """Generate questions of a specific type"""
        questions = []

        for _ in range(count):
            # Select random content segment
            segment = random.choice(content_segments)

            try:
                if question_type == QuestionType.MULTIPLE_CHOICE:
                    question = self._generate_multiple_choice(segment, config)
                elif question_type == QuestionType.FILL_BLANK:
                    question = self._generate_fill_blank(segment, config)
                elif question_type == QuestionType.SHORT_ANSWER:
                    question = self._generate_short_answer(segment, config)
                elif question_type == QuestionType.ESSAY:
                    question = self._generate_essay(segment, config)
                else:
                    continue

                if question:
                    questions.append(question)

            except Exception as e:
                logger.warning(f"Failed to generate {question_type.value} question: {e}")
                continue

        return questions

    def _generate_multiple_choice(self, segment: Dict, config: ExamConfig) -> Optional[Question]:
        """Generate a multiple choice question"""
        content = segment['content']

        # Extract key concepts for question generation
        sentences = content.split('.')
        if len(sentences) < 2:
            return None

        # Use first sentence as basis for question
        base_sentence = sentences[0].strip()

        # Create question by replacing a key term
        words = base_sentence.split()
        if len(words) < 5:
            return None

        # Find a good word to replace (noun or important term)
        key_word = None
        for word in words:
            if len(word) > 4 and word.isalpha():
                key_word = word
                break

        if not key_word:
            key_word = words[-1]

        question_text = base_sentence.replace(key_word, "______")

        # Generate options
        correct_answer = key_word
        wrong_options = self._generate_wrong_options(correct_answer, segment['topic'])

        options = [correct_answer] + wrong_options[:3]  # 4 options total
        random.shuffle(options)

        return Question(
            id=str(uuid.uuid4()),
            type=QuestionType.MULTIPLE_CHOICE,
            question_text=f"Fill in the blank: {question_text}",
            options=options,
            correct_answer=correct_answer,
            explanation=f"Based on the content: {content[:100]}...",
            topic=segment['topic'],
            images=segment.get('images', []) if config.include_images else []
        )

    def _generate_fill_blank(self, segment: Dict, config: ExamConfig) -> Optional[Question]:
        """Generate a fill-in-the-blank question"""
        content = segment['content']
        sentences = content.split('.')

        if not sentences:
            return None

        sentence = sentences[0].strip()
        words = sentence.split()

        if len(words) < 5:
            return None

        # Remove a key word
        key_word_index = len(words) // 2  # Middle word
        key_word = words[key_word_index]

        question_words = words.copy()
        question_words[key_word_index] = "______"
        question_text = " ".join(question_words)

        return Question(
            id=str(uuid.uuid4()),
            type=QuestionType.FILL_BLANK,
            question_text=question_text,
            correct_answer=key_word,
            explanation=f"The missing word completes the sentence from: {content[:100]}...",
            topic=segment['topic'],
            images=segment.get('images', []) if config.include_images else []
        )

    def _generate_short_answer(self, segment: Dict, config: ExamConfig) -> Optional[Question]:
        """Generate a short answer question"""
        content = segment['content']

        # Generate question based on content
        question_starters = [
            "What is",
            "How does",
            "Why is",
            "Explain",
            "Define",
            "Describe"
        ]

        starter = random.choice(question_starters)
        topic_words = segment['topic'].replace('_', ' ')

        question_text = f"{starter} {topic_words}?"

        return Question(
            id=str(uuid.uuid4()),
            type=QuestionType.SHORT_ANSWER,
            question_text=question_text,
            correct_answer=content[:200] + "..." if len(content) > 200 else content,
            explanation="Answer should be based on the provided content.",
            topic=segment['topic'],
            images=segment.get('images', []) if config.include_images else []
        )

    def _generate_essay(self, segment: Dict, config: ExamConfig) -> Optional[Question]:
        """Generate an essay question"""
        topic_words = segment['topic'].replace('_', ' ')

        essay_prompts = [
            f"Discuss the importance of {topic_words} in modern technology.",
            f"Analyze the key concepts and applications of {topic_words}.",
            f"Compare and contrast different approaches to {topic_words}.",
            f"Evaluate the impact of {topic_words} on society.",
            f"Explain the fundamental principles of {topic_words} with examples."
        ]

        question_text = random.choice(essay_prompts)

        return Question(
            id=str(uuid.uuid4()),
            type=QuestionType.ESSAY,
            question_text=question_text,
            correct_answer="Essay response should demonstrate understanding of the topic with specific examples and analysis.",
            explanation=f"Base your answer on: {segment['content']}",
            topic=segment['topic'],
            images=segment.get('images', []) if config.include_images else []
        )

    def _generate_wrong_options(self, correct_answer: str, topic: str) -> List[str]:
        """Generate plausible wrong options for multiple choice"""
        # Simple implementation - in practice, this could use more sophisticated methods
        wrong_options = [
            f"Alternative {correct_answer}",
            f"Modified {correct_answer}",
            f"Different {correct_answer}",
            f"Other {correct_answer}",
            "None of the above"
        ]

        return wrong_options

    def _apply_difficulty_distribution(self, questions: List[Question],
                                     distribution: Dict[str, float]) -> List[Question]:
        """Apply difficulty distribution to questions"""
        total_questions = len(questions)

        # Calculate counts for each difficulty
        easy_count = int(total_questions * distribution.get('easy', 0.3))
        hard_count = int(total_questions * distribution.get('hard', 0.2))
        medium_count = total_questions - easy_count - hard_count

        # Assign difficulties
        for i, question in enumerate(questions):
            if i < easy_count:
                question.difficulty = 'easy'
            elif i < easy_count + medium_count:
                question.difficulty = 'medium'
            else:
                question.difficulty = 'hard'

        return questions

    def export_exam(self, exam: ExamResult, format: str) -> bytes:
        """
        Export exam to specified format

        Args:
            exam: Exam result to export
            format: Export format ('pdf', 'docx', 'json')

        Returns:
            Exported exam data

        Raises:
            ExamGenerationError: If export fails
        """
        try:
            if format.lower() == 'json':
                return self._export_to_json(exam)
            elif format.lower() == 'pdf':
                return self._export_to_pdf(exam)
            elif format.lower() == 'docx':
                return self._export_to_docx(exam)
            else:
                raise ExamGenerationError(f"Unsupported export format: {format}")

        except Exception as e:
            raise ExamGenerationError(f"Export failed: {e}")

    def _export_to_json(self, exam: ExamResult) -> bytes:
        """Export exam to JSON format"""
        exam_data = exam.export_to_dict()
        json_str = json.dumps(exam_data, indent=2, ensure_ascii=False)
        return json_str.encode('utf-8')

    def _export_to_pdf(self, exam: ExamResult) -> bytes:
        """Export exam to PDF format"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            title = Paragraph(f"Exam - {exam.exam_id}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 20))

            # Questions
            for i, question in enumerate(exam.questions, 1):
                # Question text
                q_text = Paragraph(f"<b>Question {i}:</b> {question.question_text}", styles['Normal'])
                story.append(q_text)
                story.append(Spacer(1, 10))

                # Options for multiple choice
                if question.type == QuestionType.MULTIPLE_CHOICE and question.options:
                    for j, option in enumerate(question.options):
                        opt_text = Paragraph(f"  {chr(65+j)}. {option}", styles['Normal'])
                        story.append(opt_text)
                    story.append(Spacer(1, 10))

                # Images
                if question.images:
                    img_text = Paragraph(f"<i>Related images: {', '.join(question.images)}</i>", styles['Italic'])
                    story.append(img_text)

                story.append(Spacer(1, 20))

            doc.build(story)
            return buffer.getvalue()

        except ImportError:
            raise ExamGenerationError("ReportLab not available for PDF export. Install with: pip install reportlab")

    def _export_to_docx(self, exam: ExamResult) -> bytes:
        """Export exam to DOCX format"""
        try:
            from docx import Document
            from docx.shared import Inches

            doc = Document()

            # Title
            title = doc.add_heading(f'Exam - {exam.exam_id}', 0)

            # Metadata
            doc.add_paragraph(f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}')
            doc.add_paragraph(f'Questions: {len(exam.questions)}')
            doc.add_paragraph('')

            # Questions
            for i, question in enumerate(exam.questions, 1):
                # Question
                q_heading = doc.add_heading(f'Question {i}', level=2)
                doc.add_paragraph(question.question_text)

                # Options for multiple choice
                if question.type == QuestionType.MULTIPLE_CHOICE and question.options:
                    for j, option in enumerate(question.options):
                        doc.add_paragraph(f"{chr(65+j)}. {option}", style='List Bullet')

                # Images
                if question.images:
                    doc.add_paragraph(f"Related images: {', '.join(question.images)}")

                doc.add_paragraph('')  # Spacing

            # Save to buffer
            buffer = BytesIO()
            doc.save(buffer)
            return buffer.getvalue()

        except ImportError:
            raise ExamGenerationError("python-docx not available for DOCX export. Install with: pip install python-docx")

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get exam generation statistics"""
        return {
            'enabled': self.config.enable_exam_generation,
            'default_question_count': self.config.default_question_count,
            'supported_question_types': [qt.value for qt in QuestionType],
            'supported_export_formats': ['json', 'pdf', 'docx']
        }
