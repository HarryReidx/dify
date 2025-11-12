"""
Parent-child document segmenter for Enhanced Document Processing Plugin
"""

import re
import uuid
from typing import List, Optional, Dict, Tuple
import logging

from .config import DocumentProcessingConfig
from .models import DocumentSegment, HierarchyNode
from .exceptions import SegmentationError

logger = logging.getLogger(__name__)


class ParentChildSegmenter:
    """Service for creating parent-child document segments"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config

    def create_segments(self, markdown: str) -> List[DocumentSegment]:
        """
        Create document segments with parent-child relationships

        Args:
            markdown: Markdown content to segment

        Returns:
            List of document segments

        Raises:
            SegmentationError: If segmentation fails
        """
        if not self.config.enable_parent_child_segmentation:
            return self._create_simple_segments(markdown)

        try:
            # Step 1: Identify document hierarchy
            hierarchy_nodes = self.identify_hierarchy(markdown)

            if not hierarchy_nodes:
                logger.info("No hierarchy detected, using simple segmentation")
                return self._create_simple_segments(markdown)

            # Step 2: Create segments from hierarchy
            segments = self._create_segments_from_hierarchy(hierarchy_nodes, markdown)

            # Step 3: Create parent-child relationships
            self.create_parent_child_relations(segments)

            # Step 4: Optimize segment sizes
            segments = self._optimize_segment_sizes(segments)

            logger.info(f"Created {len(segments)} hierarchical segments")
            return segments

        except Exception as e:
            logger.error(f"Hierarchical segmentation failed: {e}, falling back to simple segmentation")
            return self._create_simple_segments(markdown)

    def identify_hierarchy(self, content: str) -> List[HierarchyNode]:
        """
        Identify document hierarchy from markdown headers

        Args:
            content: Markdown content

        Returns:
            List of hierarchy nodes
        """
        hierarchy_nodes = []
        lines = content.split('\n')
        current_position = 0

        # Stack to track parent nodes at each level
        parent_stack = []

        for i, line in enumerate(lines):
            line_start = current_position
            current_position += len(line) + 1  # +1 for newline

            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Find content for this section
                section_content = self._extract_section_content(lines, i, level)
                section_end = line_start + len(section_content)

                # Create hierarchy node
                node = HierarchyNode(
                    title=title,
                    level=level,
                    start_position=line_start,
                    end_position=section_end,
                    content=section_content
                )

                # Establish parent-child relationships
                # Remove nodes from stack that are at same or deeper level
                while parent_stack and parent_stack[-1].level >= level:
                    parent_stack.pop()

                # Set parent if available
                if parent_stack:
                    node.parent = parent_stack[-1]
                    parent_stack[-1].children.append(node)

                # Add to stack and result
                parent_stack.append(node)
                hierarchy_nodes.append(node)

        return hierarchy_nodes

    def _extract_section_content(self, lines: List[str], header_index: int, header_level: int) -> str:
        """Extract content for a section until next header of same or higher level"""
        section_lines = [lines[header_index]]  # Include the header

        for i in range(header_index + 1, len(lines)):
            line = lines[i]

            # Check if this is a header of same or higher level
            header_match = re.match(r'^(#{1,6})\s+', line.strip())
            if header_match:
                next_level = len(header_match.group(1))
                if next_level <= header_level:
                    break

            section_lines.append(line)

        return '\n'.join(section_lines)

    def _create_segments_from_hierarchy(self, hierarchy_nodes: List[HierarchyNode],
                                      full_content: str) -> List[DocumentSegment]:
        """Create segments from hierarchy nodes"""
        segments = []

        for node in hierarchy_nodes:
            # Create segment for this node
            segment = DocumentSegment(
                id=str(uuid.uuid4()),
                content=node.content,
                level=node.level,
                start_position=node.start_position,
                end_position=node.end_position,
                metadata={
                    'title': node.title,
                    'type': 'hierarchical',
                    'has_children': len(node.children) > 0,
                    'is_root': node.parent is None
                }
            )

            segments.append(segment)

        return segments

    def create_parent_child_relations(self, segments: List[DocumentSegment]) -> None:
        """
        Create parent-child relationships between segments

        Args:
            segments: List of segments to relate
        """
        # Sort segments by position and level
        segments.sort(key=lambda s: (s.start_position, s.level))

        # Create mapping for quick lookup
        segment_map = {seg.id: seg for seg in segments}

        for i, segment in enumerate(segments):
            # Find parent (previous segment with lower level)
            for j in range(i - 1, -1, -1):
                potential_parent = segments[j]

                if (potential_parent.level < segment.level and
                    potential_parent.start_position <= segment.start_position and
                    potential_parent.end_position >= segment.end_position):

                    segment.parent_id = potential_parent.id
                    potential_parent.children_ids.append(segment.id)
                    break

            # Find children (subsequent segments with higher level within this segment's range)
            for j in range(i + 1, len(segments)):
                potential_child = segments[j]

                if (potential_child.level > segment.level and
                    potential_child.start_position >= segment.start_position and
                    potential_child.end_position <= segment.end_position):

                    # Check if it's a direct child (not grandchild)
                    is_direct_child = True
                    for k in range(i + 1, j):
                        intermediate = segments[k]
                        if (intermediate.level < potential_child.level and
                            intermediate.level > segment.level and
                            intermediate.start_position <= potential_child.start_position and
                            intermediate.end_position >= potential_child.end_position):
                            is_direct_child = False
                            break

                    if is_direct_child and potential_child.id not in segment.children_ids:
                        segment.children_ids.append(potential_child.id)
                        potential_child.parent_id = segment.id

    def _optimize_segment_sizes(self, segments: List[DocumentSegment]) -> List[DocumentSegment]:
        """Optimize segment sizes by splitting large segments and merging small ones"""
        optimized_segments = []

        for segment in segments:
            if len(segment.content) > self.config.max_segment_length:
                # Split large segment
                split_segments = self._split_large_segment(segment)
                optimized_segments.extend(split_segments)
            elif len(segment.content) < self.config.min_segment_length:
                # Try to merge with adjacent segments
                merged_segment = self._try_merge_small_segment(segment, segments)
                if merged_segment:
                    optimized_segments.append(merged_segment)
                else:
                    optimized_segments.append(segment)
            else:
                optimized_segments.append(segment)

        return optimized_segments

    def _split_large_segment(self, segment: DocumentSegment) -> List[DocumentSegment]:
        """Split a large segment into smaller ones while preserving structure"""
        if len(segment.content) <= self.config.max_segment_length:
            return [segment]

        # Try to split at natural boundaries (paragraphs, sentences)
        split_segments = []
        lines = segment.content.split('\n')
        current_chunk = []
        current_length = 0
        chunk_start = segment.start_position

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > self.config.max_segment_length and current_chunk:
                # Create segment from current chunk
                chunk_content = '\n'.join(current_chunk)
                chunk_segment = DocumentSegment(
                    id=str(uuid.uuid4()),
                    content=chunk_content,
                    parent_id=segment.parent_id,
                    level=segment.level,
                    start_position=chunk_start,
                    end_position=chunk_start + len(chunk_content),
                    metadata={
                        **segment.metadata,
                        'split_from': segment.id,
                        'split_index': len(split_segments)
                    }
                )
                split_segments.append(chunk_segment)

                # Start new chunk with overlap
                if self.config.overlap_length > 0 and current_chunk:
                    overlap_text = current_chunk[-1]  # Last line as overlap
                    current_chunk = [overlap_text, line]
                    current_length = len(overlap_text) + line_length + 1
                else:
                    current_chunk = [line]
                    current_length = line_length

                chunk_start += len(chunk_content) - (len(overlap_text) + 1 if self.config.overlap_length > 0 else 0)
            else:
                current_chunk.append(line)
                current_length += line_length

        # Add remaining content
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunk_segment = DocumentSegment(
                id=str(uuid.uuid4()),
                content=chunk_content,
                parent_id=segment.parent_id,
                level=segment.level,
                start_position=chunk_start,
                end_position=chunk_start + len(chunk_content),
                metadata={
                    **segment.metadata,
                    'split_from': segment.id,
                    'split_index': len(split_segments)
                }
            )
            split_segments.append(chunk_segment)

        return split_segments if split_segments else [segment]

    def _try_merge_small_segment(self, segment: DocumentSegment,
                                all_segments: List[DocumentSegment]) -> Optional[DocumentSegment]:
        """Try to merge a small segment with adjacent segments"""
        # For now, just return the segment as-is
        # In a more sophisticated implementation, we could merge with siblings
        return segment

    def _create_simple_segments(self, markdown: str) -> List[DocumentSegment]:
        """
        Create simple segments without hierarchy (fallback)

        Args:
            markdown: Markdown content

        Returns:
            List of simple segments
        """
        segments = []
        lines = markdown.split('\n')
        current_content = []
        current_position = 0

        for line in lines:
            current_content.append(line)

            # Simple segmentation by length
            content_text = '\n'.join(current_content)
            if len(content_text) >= self.config.max_segment_length:
                segment = DocumentSegment(
                    id=str(uuid.uuid4()),
                    content=content_text,
                    start_position=current_position,
                    end_position=current_position + len(content_text),
                    metadata={'type': 'simple'}
                )
                segments.append(segment)

                # Handle overlap
                if self.config.overlap_length > 0:
                    overlap_text = content_text[-self.config.overlap_length:]
                    current_content = [overlap_text]
                    current_position += len(content_text) - self.config.overlap_length
                else:
                    current_content = []
                    current_position += len(content_text)

        # Add remaining content
        if current_content:
            content_text = '\n'.join(current_content)
            if len(content_text) >= self.config.min_segment_length:
                segment = DocumentSegment(
                    id=str(uuid.uuid4()),
                    content=content_text,
                    start_position=current_position,
                    end_position=current_position + len(content_text),
                    metadata={'type': 'simple'}
                )
                segments.append(segment)

        return segments

    def get_segmentation_stats(self, segments: List[DocumentSegment]) -> Dict[str, any]:
        """Get segmentation statistics"""
        if not segments:
            return {'total_segments': 0}

        hierarchical_segments = [s for s in segments if s.metadata.get('type') == 'hierarchical']
        simple_segments = [s for s in segments if s.metadata.get('type') == 'simple']

        level_distribution = {}
        for segment in hierarchical_segments:
            level = segment.level
            level_distribution[level] = level_distribution.get(level, 0) + 1

        return {
            'total_segments': len(segments),
            'hierarchical_segments': len(hierarchical_segments),
            'simple_segments': len(simple_segments),
            'level_distribution': level_distribution,
            'avg_segment_length': sum(len(s.content) for s in segments) / len(segments),
            'parent_child_relations': sum(1 for s in segments if s.parent_id),
            'root_segments': sum(1 for s in segments if not s.parent_id)
        }
