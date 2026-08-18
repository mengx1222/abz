"""知识库管理API —— CRUD + 文档上传/解析/发布流程。

遵循 api.md 中的 Admin APIs 规范：
- 知识库 CRUD
- 文档上传/解析/分块/发布/过期
- Demo模式使用内存数据
"""
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from structlog import get_logger

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.rag.pipeline import RAGPipeline, init_demo_index

logger = get_logger()
router = APIRouter()


# ============================================================
# Request / Response Schemas
# ============================================================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: str = Field("", max_length=2000, description="知识库描述")
    category: str = Field("product", description="分类：product/regulation/training/faq")
    is_public: bool = Field(True, description="是否公开")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求。"""
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    category: str | None = Field(None)
    is_public: bool | None = Field(None)
    status: str | None = Field(None, description="状态：draft/active/archived")


class DocumentUploadResponse(BaseModel):
    """文档上传结果。"""
    document_id: str
    title: str
    status: str
    chunks_count: int
    message: str


# ============================================================
# Demo 内存数据
# ============================================================

# Demo模式下的内存知识库
_demo_knowledge_bases: list[dict] = []
_demo_documents: list[dict] = []
_demo_initialized = False


async def _ensure_demo_data():
    """确保Demo数据已初始化。"""
    global _demo_initialized, _demo_knowledge_bases, _demo_documents

    if _demo_initialized:
        return

    # 初始化Demo知识库
    # organization_id: 组织范围（Task 17B）；null=未限定组织的共享知识库
    _demo_org_hq = "00000000-0000-0000-0000-000000000001"
    _demo_knowledge_bases = [
        {
            "id": "demo-kb-001",
            "name": "华安保险产品知识库",
            "description": "包含医疗险、重疾险、意外险、年金险、寿险、车险等核心产品文档",
            "category": "product",
            "status": "active",
            "document_count": 6,
            "total_chunks": 0,
            "is_public": True,
            "allowed_roles": None,
            "organization_id": _demo_org_hq,
            "version": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T00:00:00Z",
        },
        {
            "id": "demo-kb-002",
            "name": "销售话术知识库",
            "description": "各类保险产品的推荐话术和异议处理技巧",
            "category": "training",
            "status": "draft",
            "document_count": 0,
            "total_chunks": 0,
            "is_public": True,
            "allowed_roles": None,
            "organization_id": _demo_org_hq,
            "version": 1,
            "created_at": "2025-01-10T00:00:00Z",
            "updated_at": "2025-01-10T00:00:00Z",
        },
        {
            "id": "demo-kb-003",
            "name": "监管合规知识库",
            "description": "保险行业监管规定、合规要求和常见违规案例",
            "category": "regulation",
            "status": "draft",
            "document_count": 0,
            "total_chunks": 0,
            "is_public": False,
            "allowed_roles": ["HQ_ADMIN", "BRANCH_ADMIN", "COMPLIANCE"],
            "organization_id": _demo_org_hq,
            "version": 1,
            "created_at": "2025-01-12T00:00:00Z",
            "updated_at": "2025-01-12T00:00:00Z",
        },
    ]

    # 初始化Demo文档
    from app.rag.parser import get_demo_documents
    demo_docs = get_demo_documents()
    for i, doc in enumerate(demo_docs):
        _demo_documents.append({
            "id": f"demo-doc-{i+1:03d}",
            "knowledge_base_id": "demo-kb-001",
            "title": doc["title"],
            "file_name": doc["file_name"],
            "file_type": doc["file_type"],
            "file_size": len(doc["content"]),
            "status": "published",
            "chunk_count": 0,
            "published_at": "2025-01-15T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T00:00:00Z",
        })

    # 初始化RAG索引
    await init_demo_index()

    _demo_initialized = True
    logger.info("demo_knowledge_data_initialized")


# ============================================================
# Knowledge Base CRUD
# ============================================================

@router.get(
    "/knowledge-bases",
    summary="获取知识库列表",
    response_model=SuccessResponse,
)
async def list_knowledge_bases(
    request: Request,
    category: str | None = Query(None, description="按分类筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """获取知识库列表。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    kbs = _demo_knowledge_bases
    if category:
        kbs = [kb for kb in kbs if kb["category"] == category]
    if status:
        kbs = [kb for kb in kbs if kb["status"] == status]

    return SuccessResponse(data=kbs, request_id=request_id)


@router.post(
    "/knowledge-bases",
    summary="创建知识库",
    response_model=SuccessResponse,
)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """创建新知识库。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    kb = {
        "id": f"demo-kb-{uuid.uuid4().hex[:8]}",
        "name": body.name,
        "description": body.description,
        "category": body.category,
        "status": "draft",
        "document_count": 0,
        "total_chunks": 0,
        "is_public": body.is_public,
        "allowed_roles": None,
        "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
        "version": 1,
        "created_at": "2025-01-20T00:00:00Z",
        "updated_at": "2025-01-20T00:00:00Z",
    }
    _demo_knowledge_bases.append(kb)

    return SuccessResponse(data=kb, request_id=request_id)


@router.get(
    "/knowledge-bases/{kb_id}",
    summary="获取知识库详情",
    response_model=SuccessResponse,
)
async def get_knowledge_base(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """获取知识库详情。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    kb = next((kb for kb in _demo_knowledge_bases if kb["id"] == kb_id), None)
    if not kb:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})

    return SuccessResponse(data=kb, request_id=request_id)


@router.put(
    "/knowledge-bases/{kb_id}",
    summary="更新知识库",
    response_model=SuccessResponse,
)
async def update_knowledge_base(
    kb_id: str,
    body: KnowledgeBaseUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """更新知识库信息。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    kb = next((kb for kb in _demo_knowledge_bases if kb["id"] == kb_id), None)
    if not kb:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})

    if body.name is not None:
        kb["name"] = body.name
    if body.description is not None:
        kb["description"] = body.description
    if body.category is not None:
        kb["category"] = body.category
    if body.is_public is not None:
        kb["is_public"] = body.is_public
    if body.status is not None:
        kb["status"] = body.status
    kb["version"] += 1

    return SuccessResponse(data=kb, request_id=request_id)


@router.delete(
    "/knowledge-bases/{kb_id}",
    summary="删除知识库",
    response_model=SuccessResponse,
)
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """删除知识库。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    global _demo_knowledge_bases
    original_len = len(_demo_knowledge_bases)
    _demo_knowledge_bases = [kb for kb in _demo_knowledge_bases if kb["id"] != kb_id]

    if len(_demo_knowledge_bases) == original_len:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})

    return SuccessResponse(data={"message": "知识库已删除"}, request_id=request_id)


# ============================================================
# Document Management
# ============================================================

@router.get(
    "/knowledge-bases/{kb_id}/documents",
    summary="获取知识库下的文档列表",
    response_model=SuccessResponse,
)
async def list_documents(
    kb_id: str,
    request: Request,
    status: str | None = Query(None, description="按状态筛选"),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """获取知识库下的文档列表。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    docs = [d for d in _demo_documents if d["knowledge_base_id"] == kb_id]
    if status:
        docs = [d for d in docs if d["status"] == status]

    return SuccessResponse(data=docs, request_id=request_id)


@router.post(
    "/knowledge-bases/{kb_id}/documents/upload",
    summary="上传文档到知识库",
    response_model=SuccessResponse,
)
async def upload_document(
    kb_id: str,
    request: Request,
    file: UploadFile = File(..., description="上传文件"),
    title: str = Form("", description="文档标题"),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """上传文档并自动解析、分块。

    支持 TXT、Markdown、JSON 格式文件。
    """
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    # 检查知识库是否存在
    kb = next((kb for kb in _demo_knowledge_bases if kb["id"] == kb_id), None)
    if not kb:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})

    # 读取文件内容
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("gbk", errors="replace")

    file_name = file.filename or "unknown.txt"
    file_type = file_name.rsplit(".", 1)[-1] if "." in file_name else "txt"
    doc_title = title or file_name.rsplit(".", 1)[0]

    # RAG入库（携带 KB 权限策略，供 Demo 检索权限过滤）
    pipeline = RAGPipeline()
    result = await pipeline.index_document(
        content=content,
        file_type=file_type,
        title=doc_title,
        file_name=file_name,
        knowledge_base_id=kb_id,
        kb_allowed_roles=kb.get("allowed_roles"),
        kb_org_id=kb.get("organization_id"),
    )

    # 创建文档记录
    doc = {
        "id": f"demo-doc-{uuid.uuid4().hex[:8]}",
        "knowledge_base_id": kb_id,
        "title": doc_title,
        "file_name": file_name,
        "file_type": file_type,
        "file_size": len(content_bytes),
        "status": "published",
        "chunk_count": result["chunks_count"],
        "published_at": "2025-01-20T00:00:00Z",
        "created_at": "2025-01-20T00:00:00Z",
        "updated_at": "2025-01-20T00:00:00Z",
    }
    _demo_documents.append(doc)

    # 更新知识库统计
    kb["document_count"] = len([d for d in _demo_documents if d["knowledge_base_id"] == kb_id])
    kb["total_chunks"] = sum(d.get("chunk_count", 0) for d in _demo_documents if d["knowledge_base_id"] == kb_id)
    kb["updated_at"] = "2025-01-20T00:00:00Z"

    logger.info(
        "document_uploaded",
        kb_id=kb_id,
        doc_id=doc["id"],
        title=doc_title,
        chunks=result["chunks_count"],
    )

    return SuccessResponse(data={
        "document_id": doc["id"],
        "title": doc_title,
        "status": "published",
        "chunks_count": result["chunks_count"],
        "message": f"文档上传成功，已解析为 {result['chunks_count']} 个知识块",
    }, request_id=request_id)


@router.post(
    "/knowledge-bases/{kb_id}/documents/{doc_id}/publish",
    summary="发布文档",
    response_model=SuccessResponse,
)
async def publish_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """发布文档（使文档内容可被AI检索）。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    doc = next(
        (d for d in _demo_documents if d["id"] == doc_id and d["knowledge_base_id"] == kb_id),
        None,
    )
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "文档不存在"})

    doc["status"] = "published"
    doc["published_at"] = "2025-01-20T00:00:00Z"

    return SuccessResponse(data=doc, request_id=request_id)


@router.delete(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    summary="删除文档",
    response_model=SuccessResponse,
)
async def delete_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """删除文档。"""
    request_id = getattr(request.state, "request_id", None)

    await _ensure_demo_data()

    global _demo_documents
    original_len = len(_demo_documents)
    _demo_documents = [d for d in _demo_documents if not (d["id"] == doc_id and d["knowledge_base_id"] == kb_id)]

    if len(_demo_documents) == original_len:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "文档不存在"})

    return SuccessResponse(data={"message": "文档已删除"}, request_id=request_id)
