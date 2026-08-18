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
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from structlog import get_logger

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.knowledge_repository import KnowledgeBaseRepository
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
    organization_id: str | None = Field(None, description="所属组织（缺省=当前用户组织；SYSTEM_ADMIN/HQ_ADMIN/BRANCH_ADMIN 可指定）")
    allowed_roles: list[str] | None = Field(None, description="允许访问的角色列表（null=全员，Task 17B 语义）")
    metadata: dict | None = Field(None, description="扩展元数据")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求。"""
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    category: str | None = Field(None)
    is_public: bool | None = Field(None)
    status: str | None = Field(None, description="状态：draft/active/archived")
    metadata: dict | None = Field(None, description="扩展元数据（整体替换）")


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
# Production helpers（Task 21）
# ============================================================

_MANAGE_ROLES = {"SYSTEM_ADMIN", "HQ_ADMIN", "BRANCH_ADMIN", "TEAM_LEADER"}


def _kb_to_dict(kb) -> dict:
    """ORM KnowledgeBase → 与 Demo 响应一致的结构。"""
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description or "",
        "category": kb.category,
        "status": kb.status,
        "document_count": kb.document_count or 0,
        "total_chunks": kb.total_chunks or 0,
        "is_public": kb.is_public,
        "allowed_roles": kb.allowed_roles,
        "organization_id": str(kb.organization_id) if kb.organization_id else None,
        "version": kb.version or 1,
        "metadata": kb.metadata_,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
    }


def _user_role_code(user: User) -> str:
    role = getattr(user, "role", None)
    return getattr(role, "code", "") or ""


def _can_manage_kb(user: User, kb) -> bool:
    """写操作权限：管理者角色 或 创建者本人。"""
    if _user_role_code(user) in _MANAGE_ROLES:
        return True
    return kb.created_by is not None and kb.created_by == user.id


def _resolve_org_id(body_org: str | None, user: User) -> str | None:
    """解析创建 KB 的组织归属：显式指定需管理角色，否则用当前用户组织。"""
    if body_org:
        role_code = _user_role_code(user)
        if role_code not in _MANAGE_ROLES:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "无权限指定知识库所属组织"},
            )
        return body_org
    return str(user.organization_id) if user.organization_id else None


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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """获取知识库列表。

    Production 模式：DB 查询 + Task 17B 可见性过滤（角色 + 组织范围）。
    Demo 模式：内存数据（兼容）。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        from app.core.authorization import DataPermissionChecker
        checker = DataPermissionChecker(current_user)
        accessible_org_ids = checker.filter_accessible_org_ids()
        repo = KnowledgeBaseRepository(db)
        records, _total = await repo.list_knowledge_bases(
            category=category,
            status=status,
            user_roles=[_user_role_code(current_user)],
            accessible_org_ids=accessible_org_ids,
        )
        return SuccessResponse(data=[_kb_to_dict(kb) for kb in records], request_id=request_id)

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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """创建新知识库。

    Production 模式：DB insert（组织/角色/metadata 支持）；同名冲突 → 409。
    Demo 模式：内存数据（兼容）。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        org_id = _resolve_org_id(body.organization_id, current_user)
        org_uuid = uuid.UUID(org_id) if org_id else None
        repo = KnowledgeBaseRepository(db)
        if await repo.name_exists(body.name, org_uuid):
            raise HTTPException(
                status_code=409,
                detail={"code": "DUPLICATE_NAME", "message": "知识库名称已存在"},
            )
        kb = await repo.create_knowledge_base(
            name=body.name,
            description=body.description,
            category=body.category,
            is_public=body.is_public,
            organization_id=org_uuid,
            allowed_roles=body.allowed_roles,
            metadata_=body.metadata,
            created_by=current_user.id,
        )
        await db.commit()
        logger.info("knowledge_base_created", kb_id=str(kb.id), name=kb.name, org=str(org_uuid))
        return SuccessResponse(data=_kb_to_dict(kb), request_id=request_id)

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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """获取知识库详情。

    Production 模式：DB 查询 + 可见性过滤（越权/不存在 → 404）。
    Demo 模式：内存数据（兼容）。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        from app.core.authorization import DataPermissionChecker
        checker = DataPermissionChecker(current_user)
        repo = KnowledgeBaseRepository(db)
        kb = await repo.get_knowledge_base(
            uuid.UUID(kb_id),
            user_roles=[_user_role_code(current_user)],
            accessible_org_ids=checker.filter_accessible_org_ids(),
        )
        if kb is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})
        return SuccessResponse(data=_kb_to_dict(kb), request_id=request_id)

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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """更新知识库信息。

    Production 模式：DB update（写权限：管理者或创建者；越权 → 403）。
    Demo 模式：内存数据（兼容）。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        from app.core.authorization import DataPermissionChecker
        checker = DataPermissionChecker(current_user)
        repo = KnowledgeBaseRepository(db)
        kb = await repo.get_knowledge_base(
            uuid.UUID(kb_id),
            user_roles=[_user_role_code(current_user)],
            accessible_org_ids=checker.filter_accessible_org_ids(),
        )
        if kb is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})
        if not _can_manage_kb(current_user, kb):
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "无权限修改该知识库"},
            )
        if body.name is not None and await repo.name_exists(body.name, kb.organization_id, exclude_id=kb.id):
            raise HTTPException(
                status_code=409,
                detail={"code": "DUPLICATE_NAME", "message": "知识库名称已存在"},
            )
        updated = await repo.update_knowledge_base(
            kb.id,
            name=body.name,
            description=body.description,
            category=body.category,
            status=body.status,
            is_public=body.is_public,
            metadata_=body.metadata,
            updated_by=current_user.id,
        )
        await db.commit()
        return SuccessResponse(data=_kb_to_dict(updated), request_id=request_id)

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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """删除知识库。

    Production 模式：DB 物理删除（FK CASCADE 级联删文档/chunk；写权限同 update）。
    Demo 模式：内存数据（兼容）。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        from app.core.authorization import DataPermissionChecker
        checker = DataPermissionChecker(current_user)
        repo = KnowledgeBaseRepository(db)
        kb = await repo.get_knowledge_base(
            uuid.UUID(kb_id),
            user_roles=[_user_role_code(current_user)],
            accessible_org_ids=checker.filter_accessible_org_ids(),
        )
        if kb is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})
        if not _can_manage_kb(current_user, kb):
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "无权限删除该知识库"},
            )
        await repo.delete_knowledge_base(kb.id)
        await db.commit()
        logger.info("knowledge_base_deleted", kb_id=str(kb.id))
        return SuccessResponse(data={"message": "知识库已删除"}, request_id=request_id)

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
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """上传文档并自动解析、分块、入库。

    支持 TXT、Markdown、JSON 格式文件。
    Demo 模式：写入内存检索器（演示）。
    Production 模式：解析 → 分块 → AIGateway 嵌入 → 持久化到 PostgreSQL + pgvector
    （Document / DocumentChunk，带权限与产品 metadata），事务失败整体回滚。
    """
    request_id = getattr(request.state, "request_id", None)

    if not settings.DEMO_MODE:
        # ---- 生产模式：真实入库 ----
        from sqlalchemy import select as sa_select
        from app.models.knowledge import KnowledgeBase as KBModel

        try:
            kb_uuid = uuid.UUID(kb_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})
        kb_row = (
            await db.execute(sa_select(KBModel).where(KBModel.id == kb_uuid))
        ).scalar_one_or_none()
        if kb_row is None:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在"})

        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("gbk", errors="replace")
        file_name = file.filename or "unknown.txt"
        file_type = file_name.rsplit(".", 1)[-1] if "." in file_name else "txt"
        doc_title = title or file_name.rsplit(".", 1)[0]

        pipeline = RAGPipeline(db=db)
        try:
            result = await pipeline.index_document(
                content=content,
                file_type=file_type,
                title=doc_title,
                file_name=file_name,
                knowledge_base_id=kb_id,
                kb_allowed_roles=kb_row.allowed_roles,
                kb_org_id=str(kb_row.organization_id) if kb_row.organization_id else None,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={"code": "INGESTION_ERROR", "message": f"文档入库失败: {e}"},
            )

        logger.info(
            "document_uploaded",
            kb_id=kb_id,
            doc_id=result["document_id"],
            title=doc_title,
            chunks=result["chunks_count"],
        )
        return SuccessResponse(data={
            "document_id": result["document_id"],
            "title": result["title"],
            "status": "published",
            "chunks_count": result["chunks_count"],
            "message": f"文档上传成功，已入库 {result['chunks_count']} 个知识块",
        }, request_id=request_id)

    # ---- Demo 模式（内存演示） ----
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
