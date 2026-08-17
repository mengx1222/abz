"""语义分块器 —— 将文档按语义边界切分为适合检索的块。

策略：优先按Markdown标题分块，块大小控制在512 token左右，
重叠50 token。简单实现使用字符长度近似token。
"""
import re
from dataclasses import dataclass

from structlog import get_logger

logger = get_logger()


@dataclass
class Chunk:
    """文档分块。"""
    content: str
    chunk_index: int
    heading: str = ""
    section: str = ""
    token_count: int = 0
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# 配置参数
CHUNK_TARGET_TOKENS = 512  # 目标token数
CHUNK_OVERLAP_TOKENS = 50  # 重叠token数
CHUNK_MIN_TOKENS = 100  # 最小token数
# 简单的中文token近似：1字符 ≈ 1.5 token
CHAR_TO_TOKEN_RATIO = 1.5


def _estimate_tokens(text: str) -> int:
    """粗略估算token数量。"""
    return int(len(text) * CHAR_TO_TOKEN_RATIO)


def _split_by_sections(text: str) -> list[dict]:
    """按Markdown标题将文本分成大块。"""
    sections: list[dict] = []
    lines = text.split("\n")
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)")
    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    for line in lines:
        match = heading_pattern.match(line)
        if match:
            # 保存之前的section
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({
                        "heading": current_heading,
                        "level": current_level,
                        "content": content,
                    })
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 最后一个section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({
                "heading": current_heading,
                "level": current_level,
                "content": content,
            })

    return sections


def _split_by_paragraphs(text: str) -> list[str]:
    """按段落分割文本。"""
    # 按空行、换行分割
    paragraphs = re.split(r"\n\s*\n|\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_document(
    content: str,
    title: str = "",
    max_tokens: int = CHUNK_TARGET_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """将文档内容分块。

    1. 先按Markdown标题切分为sections
    2. 每个section如果超过max_tokens则按段落进一步分割
    3. 添加重叠部分
    """
    if not content or not content.strip():
        return []

    max_chars = int(max_tokens / CHAR_TO_TOKEN_RATIO)
    overlap_chars = int(overlap_tokens / CHAR_TO_TOKEN_RATIO)
    min_chars = 100  # 最小字符数

    chunks: list[Chunk] = []
    chunk_index = 0

    # 先按标题分section
    sections = _split_by_sections(content)

    if not sections:
        # 没有标题则按段落分块
        return _chunk_text_fallback(content, title, max_chars, overlap_chars)

    for section in sections:
        section_heading = section["heading"]
        section_content = section["content"]
        section_tokens = _estimate_tokens(section_content)

        # 小section直接作为一个chunk
        if section_tokens <= max_tokens:
            chunks.append(Chunk(
                content=section_content,
                chunk_index=chunk_index,
                heading=section_heading,
                section=title,
                token_count=section_tokens,
                metadata={"heading": section_heading, "split_method": "section"},
            ))
            chunk_index += 1
        else:
            # 大section需要按段落分割
            paragraphs = _split_by_paragraphs(section_content)
            buffer = ""
            buffer_tokens = 0

            for para in paragraphs:
                para_tokens = _estimate_tokens(para)

                # 超长段落（本身超过 max_tokens）：先保存 buffer，再对段落硬切分，
                # 避免单个段落成为远超限制的超大 chunk
                if para_tokens > max_tokens:
                    if buffer.strip():
                        chunks.append(Chunk(
                            content=buffer.strip(),
                            chunk_index=chunk_index,
                            heading=section_heading,
                            section=title,
                            token_count=_estimate_tokens(buffer),
                            metadata={"heading": section_heading, "split_method": "paragraph"},
                        ))
                        chunk_index += 1
                    start = 0
                    while start < len(para):
                        piece = para[start:start + max_chars].strip()
                        start += max_chars
                        if not piece:
                            continue
                        chunks.append(Chunk(
                            content=piece,
                            chunk_index=chunk_index,
                            heading=section_heading,
                            section=title,
                            token_count=_estimate_tokens(piece),
                            metadata={"heading": section_heading, "split_method": "paragraph_hard"},
                        ))
                        chunk_index += 1
                    buffer = ""
                    buffer_tokens = 0
                    continue

                new_buffer = buffer + "\n" + para if buffer else para
                new_tokens = _estimate_tokens(new_buffer)

                if new_tokens > max_tokens:
                    # 先保存buffer
                    if buffer.strip():
                        chunks.append(Chunk(
                            content=buffer.strip(),
                            chunk_index=chunk_index,
                            heading=section_heading,
                            section=title,
                            token_count=_estimate_tokens(buffer),
                            metadata={"heading": section_heading, "split_method": "paragraph"},
                        ))
                        chunk_index += 1

                    # 添加重叠部分
                    if overlap_chars > 0 and len(buffer) > overlap_chars:
                        overlap_text = buffer[-overlap_chars:]
                        buffer = overlap_text + "\n" + para
                    else:
                        buffer = para
                    buffer_tokens = _estimate_tokens(buffer)
                else:
                    buffer = new_buffer
                    buffer_tokens = new_tokens

            # 保存最后buffer
            if buffer.strip():
                chunks.append(Chunk(
                    content=buffer.strip(),
                    chunk_index=chunk_index,
                    heading=section_heading,
                    section=title,
                    token_count=_estimate_tokens(buffer),
                    metadata={"heading": section_heading, "split_method": "paragraph"},
                ))
                chunk_index += 1

    # 添加上下文：每个chunk加上标题前缀
    for chunk in chunks:
        if chunk.heading and not chunk.content.startswith(chunk.heading):
            chunk.content = f"## {chunk.heading}\n{chunk.content}"

    return chunks


def _chunk_text_fallback(
    content: str,
    title: str,
    max_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    """没有标题时的分块fallback。"""
    chunks: list[Chunk] = []
    paragraphs = _split_by_paragraphs(content)
    buffer = ""
    chunk_index = 0

    for para in paragraphs:
        # 超长段落：先保存 buffer，再硬切分，避免超大 chunk
        if len(para) > max_chars:
            if buffer.strip():
                chunks.append(Chunk(
                    content=buffer.strip(),
                    chunk_index=chunk_index,
                    section=title,
                    token_count=_estimate_tokens(buffer),
                    metadata={"split_method": "paragraph_fallback"},
                ))
                chunk_index += 1
            start = 0
            while start < len(para):
                piece = para[start:start + max_chars].strip()
                start += max_chars
                if not piece:
                    continue
                chunks.append(Chunk(
                    content=piece,
                    chunk_index=chunk_index,
                    section=title,
                    token_count=_estimate_tokens(piece),
                    metadata={"split_method": "paragraph_hard_fallback"},
                ))
                chunk_index += 1
            buffer = ""
            continue

        new_buffer = buffer + "\n" + para if buffer else para

        if len(new_buffer) > max_chars and buffer:
            chunks.append(Chunk(
                content=buffer.strip(),
                chunk_index=chunk_index,
                section=title,
                token_count=_estimate_tokens(buffer),
                metadata={"split_method": "paragraph_fallback"},
            ))
            chunk_index += 1

            if overlap_chars > 0 and len(buffer) > overlap_chars:
                buffer = buffer[-overlap_chars:] + "\n" + para
            else:
                buffer = para
        else:
            buffer = new_buffer

    if buffer.strip():
        chunks.append(Chunk(
            content=buffer.strip(),
            chunk_index=chunk_index,
            section=title,
            token_count=_estimate_tokens(buffer),
            metadata={"split_method": "paragraph_fallback"},
        ))

    return chunks
