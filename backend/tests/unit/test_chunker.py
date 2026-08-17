"""chunker 分块器单元测试 —— 覆盖分块大小约束与超长段落硬切分。"""
from app.rag.chunker import (
    CHAR_TO_TOKEN_RATIO,
    CHUNK_TARGET_TOKENS,
    chunk_document,
)

MAX_CHARS = int(CHUNK_TARGET_TOKENS / CHAR_TO_TOKEN_RATIO)
# 标题前缀（## heading\n）会追加到 section 分块内容末尾，保留余量
MARGIN = 30


def test_small_document_ok():
    chunks = chunk_document(
        "# 医疗险产品\n\n## 保障范围\n医疗费用报销。\n\n## 免责条款\n既往症不赔。",
        title="医疗险",
    )
    assert len(chunks) >= 1
    assert all(c.content.strip() for c in chunks)


def test_oversized_paragraph_hard_split_fallback():
    """无标题文档中单个超长段落 → 硬切分，不能出现超大 chunk。"""
    oversized = "这是一段超长的产品说明文字。" * 80  # ~1040 字符 >> max_chars
    content = "产品概述。\n\n" + oversized + "\n\n结尾段落。"
    chunks = chunk_document(content, title="测试文档")
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.content) <= MAX_CHARS + MARGIN, f"chunk oversize: {len(c.content)}"
        assert len(c.content) < len(oversized), "单 chunk 不应包含完整超长段落"


def test_oversized_paragraph_hard_split_section():
    """带标题文档中单个超长段落 → 硬切分。"""
    oversized = "保障范围详细说明。" * 60  # ~720 字符
    content = "# 第一章 保障范围\n\n" + oversized + "\n\n# 第二章 免责条款\n\n既往症不赔。"
    chunks = chunk_document(content, title="医疗险")
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.content) <= MAX_CHARS + MARGIN, f"chunk oversize: {len(c.content)}"
        assert len(c.content) < len(oversized), "单 chunk 不应包含完整超长段落"


def test_normal_doc_chunks_within_limit():
    """普通长文档：所有 chunk 都在大小上限内（单位修正回归）。"""
    body = "住院医疗费用包含床位费、膳食费、护理费、检查检验费、治疗费、药品费、手术费、医生费。\n" * 40
    chunks = chunk_document("# 保障范围\n\n" + body, title="医疗险")
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.content) <= MAX_CHARS + MARGIN, f"chunk oversize: {len(c.content)}"
