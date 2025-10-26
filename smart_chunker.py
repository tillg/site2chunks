"""
Smart Header-Aware Text Splitter

A content-aware chunking strategy that respects document structure and size limits.
Implements intelligent splitting by finding natural breakpoints at high-level headers.

Strategy:
1. If content < chunk_size, return as single chunk
2. Find the last high-level header (≤ max_header_level) before chunk_size limit
3. Split there and continue with remaining content
4. Preserves document hierarchy and avoids tiny chunks
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Document:
    """Simple document representation compatible with LangChain."""
    page_content: str
    metadata: Dict[str, Any]


class SmartHeaderTextSplitter:
    """
    Content-aware text splitter that finds natural breakpoints at high-level headers.

    This splitter implements a greedy strategy that:
    - Checks if content fits within chunk_size
    - Finds the last high-level header before the size limit
    - Splits at that header to preserve semantic structure
    - Continues processing remaining content

    Example:
        >>> splitter = SmartHeaderTextSplitter(
        ...     chunk_size=1200,
        ...     chunk_overlap=150,
        ...     max_header_level=3
        ... )
        >>> docs = splitter.split_text(markdown_text)
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 150,
        max_header_level: int = 3,
        strip_headers: bool = False,
    ):
        """
        Initialize the smart header text splitter.

        Args:
            chunk_size: Target maximum size for chunks (in characters)
            chunk_overlap: Number of characters to overlap between chunks
            max_header_level: Maximum header level to use as split point (1-6)
                            1 = only H1, 2 = H1-H2, 3 = H1-H3, etc.
            strip_headers: If True, remove headers from chunk content
        """
        if not 1 <= max_header_level <= 6:
            raise ValueError("max_header_level must be between 1 and 6")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_header_level = max_header_level
        self.strip_headers = strip_headers

        # Build regex pattern for headers up to max_header_level
        # Matches: # Header, ## Header, ### Header, etc.
        header_patterns = []
        for level in range(1, max_header_level + 1):
            # Match header at start of line: "# " or "## " or "### ", etc.
            header_patterns.append(f"^{'#' * level} .+$")

        # Combine all patterns
        self.header_pattern = re.compile(
            '|'.join(header_patterns),
            re.MULTILINE
        )

    def _find_header_positions(self, text: str) -> List[Tuple[int, int, str, int]]:
        """
        Find all header positions in text.

        Returns:
            List of (start_pos, end_pos, header_text, level) tuples
        """
        positions = []
        for match in self.header_pattern.finditer(text):
            header_text = match.group(0)
            # Count leading # to determine level
            level = len(header_text) - len(header_text.lstrip('#'))
            positions.append((
                match.start(),
                match.end(),
                header_text,
                level
            ))
        return positions

    def _extract_metadata_from_headers(
        self,
        text: str,
        start_pos: int,
        end_pos: int
    ) -> Dict[str, Any]:
        """
        Extract header hierarchy metadata for a chunk.

        Args:
            text: Full text
            start_pos: Start position of chunk
            end_pos: End position of chunk

        Returns:
            Dictionary with section metadata
        """
        # Find all headers before this chunk to build breadcrumb
        all_headers = self._find_header_positions(text)

        # Headers that appear before or at chunk start
        breadcrumb = []
        section_headers = {}

        # Track the most recent header at each level
        current_path = {}

        for pos, _, header_text, level in all_headers:
            if pos < end_pos:  # Header is before chunk end
                # Clean header text (remove leading #)
                clean_header = header_text.lstrip('#').strip()

                # Update current path at this level
                current_path[level] = clean_header

                # Clear deeper levels (we've entered a new section)
                current_path = {k: v for k, v in current_path.items() if k <= level}

                # If this header is at or before chunk start, it's part of our hierarchy
                if pos <= start_pos:
                    section_headers[f'h{level}'] = clean_header

        # Build breadcrumb from section_headers
        for level in range(1, self.max_header_level + 1):
            key = f'h{level}'
            if key in section_headers:
                breadcrumb.append(section_headers[key])

        return {
            'section_path': breadcrumb,
            'section_level': len(breadcrumb),
            'section_headers': section_headers
        }

    def _find_best_split_point(
        self,
        text: str,
        max_pos: int,
        min_pos: int = 0
    ) -> Tuple[Optional[int], bool]:
        """
        Find the best split point using hierarchical fallback strategy.

        Priority (from best to worst):
        1. High-level headers (up to max_header_level)
        2. Lower-level headers (beyond max_header_level)
        3. Paragraph breaks (double newline)
        4. Sentence endings (. ! ?)
        5. Comma breaks
        6. Word boundaries (space)
        7. None (caller will use hard cut at max_pos)

        Args:
            text: Text to search
            max_pos: Maximum position to search up to
            min_pos: Minimum position to consider (avoid tiny chunks)

        Returns:
            Tuple of (position, is_header_split):
            - position: Best split point, or None if no suitable point found
            - is_header_split: True if split at a header (no overlap needed)
        """
        # Strategy 1: High-level headers (H1-H{max_header_level})
        # Only use if min_pos constraint is satisfied (avoids tiny first chunks)
        headers = self._find_header_positions(text)
        best_pos = None
        for pos, _, _header, _level in headers:
            if min_pos < pos < max_pos:
                best_pos = pos
            elif pos >= max_pos:
                break
        if best_pos is not None:
            return (best_pos, True)  # Header split, no overlap needed

        # Strategy 2: Lower-level headers (beyond max_header_level)
        # Only use if min_pos is 0 (not first chunk)
        if self.max_header_level < 6 and min_pos == 0:
            lower_header_pattern = re.compile(
                '|'.join([
                    f"^{'#' * level} .+$"
                    for level in range(self.max_header_level + 1, 7)
                ]),
                re.MULTILINE
            )
            for match in lower_header_pattern.finditer(text):
                pos = match.start()
                if min_pos < pos < max_pos:
                    best_pos = pos
                elif pos >= max_pos:
                    break
            if best_pos is not None:
                return (best_pos, True)  # Header split, no overlap needed

        # Strategy 3: Paragraph breaks (double newline)
        # Find all occurrences of \n\n
        pos = text.rfind('\n\n', min_pos, max_pos)
        if pos > min_pos:
            return (pos + 2, False)  # Non-header split, use overlap

        # Strategy 4: Sentence endings
        # Look for ". ", "! ", "? " (with space after)
        for pattern in ['. ', '! ', '? ']:
            pos = text.rfind(pattern, min_pos, max_pos)
            if pos > min_pos:
                return (pos + len(pattern), False)  # Non-header split, use overlap

        # Strategy 5: Comma breaks
        pos = text.rfind(', ', min_pos, max_pos)
        if pos > min_pos:
            return (pos + 2, False)  # Non-header split, use overlap

        # Strategy 6: Word boundaries
        pos = text.rfind(' ', min_pos, max_pos)
        if pos > min_pos:
            return (pos + 1, False)  # Non-header split, use overlap

        # Strategy 7: No good break found
        return (None, False)

    def split_text(self, text: str) -> List[Document]:
        """
        Split text into chunks using smart header-aware strategy.

        Args:
            text: Markdown text to split

        Returns:
            List of Document objects with page_content and metadata
        """
        if not text or not text.strip():
            return []

        chunks = []
        current_pos = 0
        # Minimum size for first chunk to avoid tiny orphans
        # Set to 1/3 of chunk_size to ensure meaningful content
        min_chunk_size = self.chunk_size // 3

        while current_pos < len(text):
            remaining_text = text[current_pos:]

            # If remaining content fits in chunk_size, take it all
            if len(remaining_text) <= self.chunk_size:
                chunk_text = remaining_text.strip()
                if chunk_text:  # Only add non-empty chunks
                    metadata = self._extract_metadata_from_headers(
                        text, current_pos, len(text)
                    )
                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata=metadata
                    ))
                break

            # Find best split point using hierarchical fallback strategy
            # For first chunk, ensure split creates a chunk >= min_chunk_size
            # For subsequent chunks, no minimum position constraint
            min_pos = min_chunk_size if len(chunks) == 0 else 0
            split_pos, is_header_split = self._find_best_split_point(
                remaining_text,
                self.chunk_size,
                min_pos
            )

            if split_pos is None:
                # No suitable split point found, fall back to chunk_size
                chunk_end = current_pos + self.chunk_size
                is_header_split = False
            else:
                chunk_end = current_pos + split_pos

            # Extract chunk
            chunk_text = text[current_pos:chunk_end].strip()

            # Add chunk with size filtering
            # Always add first chunk (even if small, might be title/intro)
            # For subsequent chunks, skip if too small (likely just a header with no content)
            should_add = False
            if chunk_text:
                if len(chunks) == 0:
                    # First chunk - always add if non-empty
                    should_add = True
                elif len(chunk_text) >= min_chunk_size:
                    # Subsequent chunk with enough content
                    should_add = True
                # else: skip tiny middle chunks (< 100 chars)

            if should_add:
                metadata = self._extract_metadata_from_headers(
                    text, current_pos, chunk_end
                )
                chunks.append(Document(
                    page_content=chunk_text,
                    metadata=metadata
                ))

            # Move to next position
            if is_header_split:
                # We split at a header - this is a semantic boundary, no overlap needed
                # Move to the split position (the header itself)
                current_pos = chunk_end
            elif self.chunk_overlap > 0:
                # Non-header split (paragraph, sentence, word, etc.), use overlap for continuity
                # Back up by overlap amount from chunk end
                current_pos = max(chunk_end - self.chunk_overlap, current_pos + 1)
            else:
                # No overlap configured - just move to chunk end
                current_pos = chunk_end

            # Safety check to prevent infinite loops
            if current_pos >= len(text):
                break

        return chunks


class LegacyLangChainSplitter:
    """
    Wrapper for the original two-stage LangChain splitting strategy.

    This implements the current behavior in chunk.py:
    1. MarkdownHeaderTextSplitter - splits at all headers
    2. MarkdownTextSplitter - further splits large sections
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 150,
        headers_to_split_on: List[Tuple[str, str]] = None,
    ):
        """
        Initialize legacy splitter.

        Args:
            chunk_size: Target maximum size for chunks
            chunk_overlap: Number of characters to overlap
            headers_to_split_on: List of (header, name) tuples like [('#', 'h1')]
        """
        from langchain_text_splitters import (
            MarkdownHeaderTextSplitter,
            MarkdownTextSplitter,
        )

        if headers_to_split_on is None:
            headers_to_split_on = [
                ('#', 'h1'), ('##', 'h2'), ('###', 'h3'),
                ('####', 'h4'), ('#####', 'h5'), ('######', 'h6')
            ]

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.headers_to_split_on = headers_to_split_on

        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )

        self.md_splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split_text(self, text: str) -> List[Document]:
        """
        Split text using two-stage strategy.

        Args:
            text: Markdown text to split

        Returns:
            List of Document objects
        """
        # Stage 1: Split by headers
        header_docs = self.header_splitter.split_text(text)

        # Stage 2: Further split large sections
        result_docs = []
        for sect_doc in header_docs:
            sect_text = sect_doc.page_content
            sect_meta = dict(sect_doc.metadata or {})

            # Extract breadcrumb from metadata
            breadcrumb = []
            for key in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if key in sect_meta and sect_meta[key]:
                    breadcrumb.append(sect_meta[key])

            level = len(breadcrumb) if breadcrumb else 0

            # Split large sections
            sub_chunks = self.md_splitter.split_text(sect_text)
            for sub in sub_chunks:
                result_docs.append(Document(
                    page_content=sub.strip(),
                    metadata={
                        'section_meta': sect_meta,
                        'section_breadcrumb': breadcrumb,
                        'section_level': level,
                    }
                ))

        return result_docs
