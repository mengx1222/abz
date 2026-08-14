import json
from datetime import datetime, timezone, timedelta
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.ai.gateway import get_ai_gateway
from app.repositories.customer_repo import (
    CustomerRepository,
    CustomerInteractionRepository,
    CustomerFollowupRepository,
)
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerDetail,
    CustomerOut,
    InteractionOut,
    FollowupOut,
    CustomerInteractionCreate,
    CustomerFollowupCreate,
    CustomerAnalysisResult,
)

logger = get_logger()

# 演示组织 ID
_DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

# ============================================================
# 20 条演示客户数据
# ============================================================
_DEMO_CUSTOMERS: list[dict] = []
_DEMO_INTERACTIONS: list[dict] = []
_DEMO_FOLLOWUPS: list[dict] = []
_DEMO_INITIALIZED = False


def _build_demo_data() -> None:
    """构造 20 条演示客户及其互动、跟进数据。"""
    global _DEMO_INITIALIZED, _DEMO_CUSTOMERS, _DEMO_INTERACTIONS, _DEMO_FOLLOWUPS

    if _DEMO_INITIALIZED:
        return

    now = datetime.now(timezone.utc)
    base = now - timedelta(days=60)

    customers_raw = [
        {"name": "陈志明", "age": 45, "gender": "male", "phone": "13912345001", "customer_type": "active", "tags": ["高净值", "企业主"], "insurance_type": "重疾险", "current_stage": "negotiation", "intention_level": 5, "source_channel": "转介绍", "notes": "拥有3家企业，年缴保费预算50万+"},
        {"name": "王丽华", "age": 38, "gender": "female", "phone": "13912345002", "customer_type": "active", "tags": ["白领", "家庭保障"], "insurance_type": "医疗险", "current_stage": "proposal", "intention_level": 4, "source_channel": "线上咨询", "notes": "有两位子女，关注教育金和医疗"},
        {"name": "李伟强", "age": 55, "gender": "male", "phone": "13912345003", "customer_type": "active", "tags": ["退休规划", "企业主"], "insurance_type": "年金险", "current_stage": "closed_won", "intention_level": 5, "source_channel": "老客户转介绍", "notes": "去年购买过年金险，考虑加保"},
        {"name": "张美玲", "age": 32, "gender": "female", "phone": "13912345004", "customer_type": "prospective", "tags": ["白领", "子女教育"], "insurance_type": "重疾险", "current_stage": "needs_analysis", "intention_level": 3, "source_channel": "微信营销", "notes": "刚生二胎，开始关注保险"},
        {"name": "刘建国", "age": 62, "gender": "male", "phone": "13912345005", "customer_type": "lapsed", "tags": ["慢病", "退休规划"], "insurance_type": "医疗险", "current_stage": "closed_lost", "intention_level": 1, "source_channel": "电话营销", "notes": "因健康告知问题未能承保"},
        {"name": "赵小芳", "age": 28, "gender": "female", "phone": "13912345006", "customer_type": "prospective", "tags": ["白领"], "insurance_type": "意外险", "current_stage": "initial_contact", "intention_level": 2, "source_channel": "线上咨询", "notes": "通过小程序咨询，对意外险感兴趣"},
        {"name": "孙浩然", "age": 42, "gender": "male", "phone": "13912345007", "customer_type": "prospective", "tags": ["高净值", "家庭保障"], "insurance_type": "寿险", "current_stage": "presentation", "intention_level": 4, "source_channel": "线下活动", "notes": "IT公司技术总监，家庭年收入80万"},
        {"name": "周雪梅", "age": 50, "gender": "female", "phone": "13912345008", "customer_type": "lapsed", "tags": ["慢病", "家庭保障"], "insurance_type": "重疾险", "current_stage": "closed_lost", "intention_level": 2, "source_channel": "电话营销", "notes": "2019年投保后因保费压力退保"},
        {"name": "吴国栋", "age": 35, "gender": "male", "phone": "13912345009", "customer_type": "prospective", "tags": ["企业主", "高净值"], "insurance_type": "医疗险", "current_stage": "proposal", "intention_level": 4, "source_channel": "商会推荐", "notes": "餐饮连锁企业老板，员工50+人"},
        {"name": "黄秀英", "age": 58, "gender": "female", "phone": "13912345010", "customer_type": "active", "tags": ["退休规划", "家庭保障"], "insurance_type": "年金险", "current_stage": "negotiation", "intention_level": 4, "source_channel": "老客户转介绍", "notes": "教师退休，关注养老补充"},
        {"name": "郑明辉", "age": 29, "gender": "male", "phone": "13912345011", "customer_type": "lapsed", "tags": ["白领"], "insurance_type": "重疾险", "current_stage": "closed_lost", "intention_level": 2, "source_channel": "线上咨询", "notes": "程序员，首次了解保险"},
        {"name": "林小红", "age": 41, "gender": "female", "phone": "13912345012", "customer_type": "lapsed", "tags": ["家庭保障", "子女教育"], "insurance_type": "医疗险", "current_stage": "presentation", "intention_level": 3, "source_channel": "转介绍", "notes": "全职妈妈，先生是企业中层"},
        {"name": "杨志豪", "age": 48, "gender": "male", "phone": "13912345013", "customer_type": "lapsed", "tags": ["企业主"], "insurance_type": "车险", "current_stage": "closed_lost", "intention_level": 1, "source_channel": "电话营销", "notes": "感觉价格不合适，选择竞品"},
        {"name": "何玉兰", "age": 36, "gender": "female", "phone": "13912345014", "customer_type": "prospective", "tags": ["白领", "家庭保障"], "insurance_type": "意外险", "current_stage": "needs_analysis", "intention_level": 3, "source_channel": "微信营销", "notes": "银行理财经理，对保险有基础认知"},
        {"name": "马俊杰", "age": 52, "gender": "male", "phone": "13912345015", "customer_type": "active", "tags": ["高净值", "企业主", "退休规划"], "insurance_type": "寿险", "current_stage": "closed_won", "intention_level": 5, "source_channel": "线下活动", "notes": "房地产公司老板，已签单终身寿险500万"},
        {"name": "徐静雯", "age": 27, "gender": "female", "phone": "13912345016", "customer_type": "prospective", "tags": ["白领"], "insurance_type": "医疗险", "current_stage": "initial_contact", "intention_level": 2, "source_channel": "线上咨询", "notes": "护士，对保险产品较了解"},
        {"name": "罗大伟", "age": 60, "gender": "male", "phone": "13912345017", "customer_type": "lapsed", "tags": ["慢病", "退休规划"], "insurance_type": "年金险", "current_stage": "closed_lost", "intention_level": 1, "source_channel": "电话营销", "notes": "投保后犹豫期退保"},
        {"name": "谢丽娜", "age": 33, "gender": "female", "phone": "13912345018", "customer_type": "prospective", "tags": ["子女教育", "家庭保障"], "insurance_type": "重疾险", "current_stage": "proposal", "intention_level": 4, "source_channel": "转介绍", "notes": "二胎妈妈，主动咨询儿童重疾险"},
        {"name": "唐国强", "age": 44, "gender": "male", "phone": "13912345019", "customer_type": "active", "tags": ["企业主", "高净值"], "insurance_type": "医疗险", "current_stage": "negotiation", "intention_level": 4, "source_channel": "商会推荐", "notes": "制造企业老板，考虑团体意外险"},
        {"name": "冯晓燕", "age": 39, "gender": "female", "phone": "13912345020", "customer_type": "prospective", "tags": ["白领", "家庭保障"], "insurance_type": "年金险", "current_stage": "needs_analysis", "intention_level": 2, "source_channel": "微信营销", "notes": "因工作调动至外地，暂时搁置"},
    ]

    for i, c in enumerate(customers_raw):
        cid = uuid.UUID(f"a0000000-0000-0000-0000-{i+1:012d}")
        created = base + timedelta(days=i * 3)
        updated = created + timedelta(days=i * 2 + 5)

        _DEMO_CUSTOMERS.append({
            "id": str(cid),
            "name": c["name"],
            "age": c["age"],
            "gender": c["gender"],
            "phone": c["phone"],
            "customer_type": c["customer_type"],
            "tags": c["tags"],
            "insurance_type": c["insurance_type"],
            "current_stage": c["current_stage"],
            "intention_level": c["intention_level"],
            "source_channel": c["source_channel"],
            "notes": c["notes"],
            "assigned_to": str(_DEMO_USER_ID),
            "organization_id": str(_DEMO_ORG_ID),
            "created_at": created.isoformat(),
            "updated_at": updated.isoformat(),
        })

        # 每个客户 1-3 条互动记录
        interaction_templates = [
            {"type": "phone", "direction": "outbound", "content": f"电话联系{c['name']}，了解保险需求", "outcome": "客户表示有兴趣，约定下次沟通时间"},
            {"type": "wechat", "direction": "inbound", "content": f"{c['name']}通过微信咨询{c['insurance_type']}产品细节", "outcome": "已发送产品对比资料"},
            {"type": "f2f", "direction": "outbound", "content": f"与{c['name']}面谈，深入分析保障需求", "outcome": "客户认可方案，进入下一阶段"},
        ]
        n_interactions = 1 + (i % 3)
        for j in range(n_interactions):
            it = interaction_templates[j]
            itime = created + timedelta(days=j * 5 + 2)
            _DEMO_INTERACTIONS.append({
                "id": str(uuid.uuid4()),
                "customer_id": str(cid),
                "type": it["type"],
                "direction": it["direction"],
                "content": it["content"],
                "outcome": it["outcome"],
                "next_followup_date": (itime + timedelta(days=7)).isoformat() if j == n_interactions - 1 else None,
                "created_at": itime.isoformat(),
            })

        # 每个客户 0-2 条跟进任务
        n_followups = i % 3
        for j in range(n_followups):
            ftime = created + timedelta(days=(j + 1) * 10)
            status = "completed" if j == 0 and i < 10 else "pending"
            _DEMO_FOLLOWUPS.append({
                "id": str(uuid.uuid4()),
                "customer_id": str(cid),
                "scheduled_date": ftime.isoformat(),
                "completed_date": (ftime + timedelta(days=1)).isoformat() if status == "completed" else None,
                "status": status,
                "content": f"跟进{c['name']}的{c['insurance_type']}方案进度",
                "result": "客户已确认，准备签约" if status == "completed" else None,
                "created_at": ftime.isoformat(),
            })

    _DEMO_INITIALIZED = True
    logger.info("demo_customer_data_initialized", customer_count=len(_DEMO_CUSTOMERS))


class CustomerService:
    """客户360服务层。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.interaction_repo = CustomerInteractionRepository(session)
        self.followup_repo = CustomerFollowupRepository(session)

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------

    async def list_customers(
        self,
        customer_type: str | None = None,
        current_stage: str | None = None,
        intention_level: int | None = None,
        tag: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取客户列表。返回 (items, total)。"""
        if settings.DEMO_MODE:
            return self._demo_list(
                customer_type, current_stage, intention_level, tag, search, page, page_size
            )

        records, total = await self.customer_repo.search_list(
            page=page,
            page_size=page_size,
            customer_type=customer_type,
            current_stage=current_stage,
            intention_level=intention_level,
            tag=tag,
            search=search,
            organization_id=_DEMO_ORG_ID,
        )
        items = [self._customer_to_dict(r) for r in records]
        return items, total

    def _demo_list(
        self,
        customer_type: str | None,
        current_stage: str | None,
        intention_level: int | None,
        tag: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        _build_demo_data()

        filtered = list(_DEMO_CUSTOMERS)
        if customer_type:
            filtered = [c for c in filtered if c["customer_type"] == customer_type]
        if current_stage:
            filtered = [c for c in filtered if c["current_stage"] == current_stage]
        if intention_level is not None:
            filtered = [c for c in filtered if c["intention_level"] == intention_level]
        if tag:
            filtered = [c for c in filtered if tag in (c.get("tags") or [])]
        if search:
            s = search.lower()
            filtered = [c for c in filtered if s in c["name"].lower() or (c.get("phone") and s in c["phone"])]

        total = len(filtered)
        start = (page - 1) * page_size
        items = filtered[start:start + page_size]
        return items, total

    # ------------------------------------------------------------------
    # 详情
    # ------------------------------------------------------------------

    async def get_customer(self, customer_id: uuid.UUID) -> dict | None:
        """获取客户详情（含互动和跟进）。"""
        if settings.DEMO_MODE:
            return self._demo_get_detail(str(customer_id))

        customer = await self.customer_repo.get_by_id_active(customer_id)
        if customer is None:
            return None
        return self._customer_detail_to_dict(customer)

    def _demo_get_detail(self, customer_id: str) -> dict | None:
        _build_demo_data()

        cust = next((c for c in _DEMO_CUSTOMERS if c["id"] == customer_id), None)
        if cust is None:
            return None

        interactions = [
            i for i in _DEMO_INTERACTIONS if i["customer_id"] == customer_id
        ]
        followups = [
            f for f in _DEMO_FOLLOWUPS if f["customer_id"] == customer_id
        ]

        return {**cust, "interactions": interactions, "followups": followups}

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------

    async def create_customer(self, data: CustomerCreate, user_id: uuid.UUID) -> dict:
        """创建客户。"""
        if settings.DEMO_MODE:
            return self._demo_create(data, user_id)

        customer = await self.customer_repo.create(
            name=data.name,
            age=data.age,
            gender=data.gender,
            phone=data.phone,
            customer_type=data.customer_type,
            tags=data.tags,
            insurance_type=data.insurance_type,
            current_stage=data.current_stage,
            intention_level=data.intention_level,
            source_channel=data.source_channel,
            notes=data.notes,
            assigned_to=user_id,
            organization_id=_DEMO_ORG_ID,
            created_by=user_id,
            updated_by=user_id,
        )
        await self.session.commit()
        return self._customer_to_dict(customer)

    def _demo_create(self, data: CustomerCreate, user_id: uuid.UUID) -> dict:
        _build_demo_data()
        now = datetime.now(timezone.utc).isoformat()

        cust = {
            "id": str(uuid.uuid4()),
            "name": data.name,
            "age": data.age,
            "gender": data.gender,
            "phone": data.phone,
            "customer_type": data.customer_type,
            "tags": data.tags,
            "insurance_type": data.insurance_type,
            "current_stage": data.current_stage,
            "intention_level": data.intention_level,
            "source_channel": data.source_channel,
            "notes": data.notes,
            "assigned_to": str(user_id),
            "organization_id": str(_DEMO_ORG_ID),
            "created_at": now,
            "updated_at": now,
        }
        _DEMO_CUSTOMERS.append(cust)
        return cust

    # ------------------------------------------------------------------
    # 更新
    # ------------------------------------------------------------------

    async def update_customer(self, customer_id: uuid.UUID, data: CustomerUpdate, user_id: uuid.UUID) -> dict | None:
        """更新客户信息。"""
        if settings.DEMO_MODE:
            return self._demo_update(str(customer_id), data, user_id)

        customer = await self.customer_repo.get_by_id_active(customer_id)
        if customer is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        if update_fields:
            update_fields["updated_by"] = user_id
            await self.customer_repo.update(customer_id, **update_fields)
            await self.session.commit()

        updated = await self.customer_repo.get_by_id(customer_id)
        return self._customer_to_dict(updated) if updated else None

    def _demo_update(self, customer_id: str, data: CustomerUpdate, user_id: uuid.UUID) -> dict | None:
        _build_demo_data()

        cust = next((c for c in _DEMO_CUSTOMERS if c["id"] == customer_id), None)
        if cust is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for k, v in update_fields.items():
            cust[k] = v
        cust["updated_at"] = datetime.now(timezone.utc).isoformat()
        return cust

    # ------------------------------------------------------------------
    # 软删除
    # ------------------------------------------------------------------

    async def delete_customer(self, customer_id: uuid.UUID) -> bool:
        """软删除客户。"""
        if settings.DEMO_MODE:
            return self._demo_delete(str(customer_id))

        customer = await self.customer_repo.get_by_id_active(customer_id)
        if customer is None:
            return False
        await self.customer_repo.soft_delete(customer_id)
        await self.session.commit()
        return True

    def _demo_delete(self, customer_id: str) -> bool:
        _build_demo_data()
        global _DEMO_CUSTOMERS
        original_len = len(_DEMO_CUSTOMERS)
        _DEMO_CUSTOMERS = [c for c in _DEMO_CUSTOMERS if c["id"] != customer_id]
        return len(_DEMO_CUSTOMERS) < original_len

    # ------------------------------------------------------------------
    # 添加互动记录
    # ------------------------------------------------------------------

    async def add_interaction(
        self, customer_id: uuid.UUID, data: CustomerInteractionCreate, user_id: uuid.UUID
    ) -> dict | None:
        """为客户添加互动记录。"""
        if settings.DEMO_MODE:
            return self._demo_add_interaction(str(customer_id), data, user_id)

        customer = await self.customer_repo.get_by_id_active(customer_id)
        if customer is None:
            return None

        interaction = await self.interaction_repo.create(
            customer_id=customer_id,
            type=data.type,
            direction=data.direction,
            content=data.content,
            outcome=data.outcome,
            next_followup_date=data.next_followup_date,
            created_by=user_id,
            updated_by=user_id,
        )
        await self.session.commit()
        return {
            "id": str(interaction.id),
            "customer_id": str(interaction.customer_id),
            "type": interaction.type,
            "direction": interaction.direction,
            "content": interaction.content,
            "outcome": interaction.outcome,
            "next_followup_date": interaction.next_followup_date.isoformat() if interaction.next_followup_date else None,
            "created_at": interaction.created_at.isoformat(),
        }

    def _demo_add_interaction(
        self, customer_id: str, data: CustomerInteractionCreate, user_id: uuid.UUID
    ) -> dict | None:
        _build_demo_data()
        cust = next((c for c in _DEMO_CUSTOMERS if c["id"] == customer_id), None)
        if cust is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        interaction = {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "type": data.type,
            "direction": data.direction,
            "content": data.content,
            "outcome": data.outcome,
            "next_followup_date": data.next_followup_date.isoformat() if data.next_followup_date else None,
            "created_at": now,
        }
        _DEMO_INTERACTIONS.append(interaction)
        return interaction

    # ------------------------------------------------------------------
    # 添加跟进任务
    # ------------------------------------------------------------------

    async def add_followup(
        self, customer_id: uuid.UUID, data: CustomerFollowupCreate, user_id: uuid.UUID
    ) -> dict | None:
        """为客户添加跟进任务。"""
        if settings.DEMO_MODE:
            return self._demo_add_followup(str(customer_id), data, user_id)

        customer = await self.customer_repo.get_by_id_active(customer_id)
        if customer is None:
            return None

        completed_date = None
        if data.status == "completed":
            completed_date = datetime.now(timezone.utc)

        followup = await self.followup_repo.create(
            customer_id=customer_id,
            scheduled_date=data.scheduled_date,
            completed_date=completed_date,
            status=data.status,
            content=data.content,
            result=data.result,
            created_by=user_id,
            updated_by=user_id,
        )
        await self.session.commit()
        return {
            "id": str(followup.id),
            "customer_id": str(followup.customer_id),
            "scheduled_date": followup.scheduled_date.isoformat(),
            "completed_date": followup.completed_date.isoformat() if followup.completed_date else None,
            "status": followup.status,
            "content": followup.content,
            "result": followup.result,
            "created_at": followup.created_at.isoformat(),
        }

    def _demo_add_followup(
        self, customer_id: str, data: CustomerFollowupCreate, user_id: uuid.UUID
    ) -> dict | None:
        _build_demo_data()
        cust = next((c for c in _DEMO_CUSTOMERS if c["id"] == customer_id), None)
        if cust is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        completed_date = now if data.status == "completed" else None
        followup = {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "scheduled_date": data.scheduled_date.isoformat(),
            "completed_date": completed_date,
            "status": data.status,
            "content": data.content,
            "result": data.result,
            "created_at": now,
        }
        _DEMO_FOLLOWUPS.append(followup)
        return followup

    # ------------------------------------------------------------------
    # AI 客户分析（SSE 流式）
    # ------------------------------------------------------------------

    async def ai_analysis_stream(
        self, customer_id: uuid.UUID
    ) -> AsyncGenerator[str, None]:
        """对指定客户进行 AI 分析，返回 SSE 事件流。"""
        # 获取客户上下文
        customer: dict | None = None
        if settings.DEMO_MODE:
            customer = self._demo_get_detail(str(customer_id))
        else:
            c_obj = await self.customer_repo.get_by_id_active(customer_id)
            if c_obj:
                customer = self._customer_detail_to_dict(c_obj)

        if customer is None:
            import json as _json
            yield f"event: error\ndata: {_json.dumps({'message': '客户不存在'}, ensure_ascii=False)}\n\n"
            return

        # 构建提示词
        prompt = self._build_analysis_prompt(customer)

        yield f"event: analysis_start\ndata: {{\"customer_id\": \"{customer_id}\"}}\n\n"

        # 调用 AI Gateway（流式）
        gateway = get_ai_gateway()
        full_content = ""

        try:
            stream = await gateway.chat(
                messages=[
                    {"role": "system", "content": "你是一位资深的保险客户分析顾问，请根据客户信息进行专业分析。所有分析结论请标注为'AI分析'。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )

            async for token in stream:
                full_content += token
                import json as _json
                yield f"event: token\ndata: {_json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("customer_ai_analysis_error", customer_id=str(customer_id), error=str(e))
            full_content = self._get_demo_analysis(customer)
            import json as _json
            yield f"event: token\ndata: {_json.dumps({'token': full_content}, ensure_ascii=False)}\n\n"

        # 尝试解析结构化数据
        structured = self._parse_analysis_result(customer, full_content)
        import json as _json
        yield f"event: structured_data\ndata: {_json.dumps(structured, ensure_ascii=False)}\n\n"
        yield f"event: analysis_complete\ndata: {{\"customer_id\": \"{customer_id}\"}}\n\n"

    def _build_analysis_prompt(self, customer: dict) -> str:
        """构建客户分析提示词。"""
        interactions_text = ""
        for i, inter in enumerate(customer.get("interactions", []), 1):
            direction = "呼入" if inter["direction"] == "inbound" else "呼出"
            type_map = {"phone": "电话", "wechat": "微信", "f2f": "面谈", "email": "邮件", "other": "其他"}
            itype = type_map.get(inter["type"], inter["type"])
            interactions_text += f"  {i}. [{itype}-{direction}] {inter.get('content', '')} | 结果: {inter.get('outcome', '无')}\n"

        followups_text = ""
        for f in customer.get("followups", []):
            status_map = {"pending": "待完成", "completed": "已完成", "cancelled": "已取消"}
            followups_text += f"  - 计划: {f.get('scheduled_date', '')} 状态: {status_map.get(f['status'], f['status'])} 内容: {f.get('content', '无')}\n"

        stage_map = {
            "initial_contact": "初步接触",
            "needs_analysis": "需求分析",
            "proposal": "方案推荐",
            "presentation": "方案展示",
            "negotiation": "谈判中",
            "closed_won": "已签单",
            "closed_lost": "已流失",
        }
        type_map = {"prospective": "准客户", "active": "活跃客户", "lapsed": "流失客户"}

        return f"""请对以下保险客户进行全面的 AI分析，并返回结构化的分析结果。

## 客户基本信息
- 姓名：{customer['name']}
- 年龄：{customer.get('age', '未知')}
- 性别：{'男' if customer.get('gender') == 'male' else '女' if customer.get('gender') == 'female' else '未知'}
- 客户类型：{type_map.get(customer['customer_type'], customer['customer_type'])}
- 当前阶段：{stage_map.get(customer['current_stage'], customer['current_stage'])}
- 意向等级：{customer['intention_level']}/5
- 标签：{'、'.join(customer.get('tags') or [])}
- 感兴趣险种：{customer.get('insurance_type', '未知')}
- 来源渠道：{customer.get('source_channel', '未知')}
- 备注：{customer.get('notes', '无')}

## 互动记录
{interactions_text if interactions_text else '  暂无互动记录'}

## 跟进任务
{followups_text if followups_text else '  暂无跟进任务'}

请分析以下维度并给出建议：
1. 客户画像总结
2. 购买意向评分（1-10分）
3. 价格敏感度（low/medium/high）
4. 推荐保险产品
5. 建议的行动方案
6. 需要避免的禁忌事项
7. 风险提示"""

    def _parse_analysis_result(self, customer: dict, ai_content: str) -> dict:
        """尝试从 AI 回复中提取结构化数据，失败则基于客户信息生成。"""
        import json as _json

        # 在 demo 模式下直接生成结构化结果
        if settings.DEMO_MODE:
            return self._generate_structured_analysis(customer)

        # 尝试从 AI 回复中提取 JSON 块
        try:
            if "```json" in ai_content:
                json_block = ai_content.split("```json")[1].split("```")[0].strip()
                return _json.loads(json_block)
        except (IndexError, _json.JSONDecodeError):
            pass

        return self._generate_structured_analysis(customer)

    def _generate_structured_analysis(self, customer: dict) -> dict:
        """基于客户信息生成结构化分析结果。"""
        stage = customer["current_stage"]
        intention = customer["intention_level"]
        tags = customer.get("tags") or []
        insurance_type = customer.get("insurance_type", "")
        name = customer["name"]
        age = customer.get("age", 35)
        notes = customer.get("notes", "")

        # 购买意向映射（1-5 内部 → 1-10 外部）
        intent_map = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}
        purchase_intent = intent_map.get(intention, 5)
        if stage == "closed_won":
            purchase_intent = 10
        elif stage == "closed_lost":
            purchase_intent = 1

        # 价格敏感度
        if "高净值" in tags:
            price_sensitivity = "low"
        elif "企业主" in tags:
            price_sensitivity = "low"
        elif "白领" in tags:
            price_sensitivity = "medium"
        else:
            price_sensitivity = "medium"

        # 推荐产品
        product_map = {
            "医疗险": ["百万医疗险", "中高端医疗险", "门诊险"],
            "重疾险": ["重疾险（多次赔付型）", "重疾险（单次赔付型）", "特定疾病险"],
            "意外险": ["综合意外险", "交通意外险", "意外医疗险"],
            "年金险": ["养老年金险", "教育年金险", "增额终身寿险"],
            "寿险": ["定期寿险", "终身寿险", "定额终身寿险"],
            "车险": ["交强险+商业车险", "驾乘险"],
        }
        recommended = product_map.get(insurance_type, ["综合保障方案"])
        if "家庭保障" in tags:
            recommended.append("家庭保障计划")
        if "子女教育" in tags:
            recommended.append("教育金保险")
        if "退休规划" in tags:
            recommended.append("商业养老保险")

        # 建议行动
        actions = []
        stage_actions = {
            "initial_contact": ["尽快安排第一次正式电话沟通", "了解客户的基本保障情况和家庭结构", "发送保险科普资料建立专业形象"],
            "needs_analysis": ["安排需求分析面谈", "了解家庭年收入和保障缺口", "制作家庭保障需求分析报告"],
            "proposal": ["根据需求分析结果制定2-3套方案", "准备产品对比资料", "预约方案展示时间"],
            "presentation": ["进行专业的方案展示", "解答客户疑虑和异议", "提供竞品对比分析"],
            "negotiation": ["针对客户关注点调整方案", "提供限时优惠或附加服务", "协助客户完成投保流程"],
            "closed_won": ["做好保单送达和讲解服务", "建立定期回访计划", "挖掘交叉销售机会"],
            "closed_lost": ["分析流失原因并记录", "保持适度联系（每季度一次）", "等待合适的再次接触时机"],
        }
        actions = stage_actions.get(stage, ["继续跟进客户需求"])

        # 禁忌事项
        forbidden = ["避免过度推销和高压销售", "不要在未充分了解需求前推荐产品"]
        if "慢病" in tags:
            forbidden.insert(0, "切勿承诺不符合健康告知条件的承保结果")
        if age > 55:
            forbidden.append("避免推荐保费过高的长期险产品")
        if "企业主" in tags:
            forbidden.append("不要忽视企业保障需求，仅关注个人")

        # 风险提示
        risks = []
        if "慢病" in tags:
            risks.append("客户存在健康问题，需关注健康告知合规性")
        if stage == "closed_lost":
            risks.append("客户已流失，需注意再次接触的时机和方式")
        if customer.get("customer_type") == "lapsed":
            risks.append("流失客户需分析历史原因，避免重复犯错")
        if age > 50:
            risks.append("高龄客户投保需注意年龄限制和保费承受能力")
        if not risks:
            risks.append("保持正常跟进频率，避免客户遗忘")

        # 客户画像
        gender_text = "男性" if customer.get("gender") == "male" else "女性" if customer.get("gender") == "female" else ""
        profile = f"AI分析 - {name}，{age}岁{gender_text}"
        if tags:
            profile += f"，标签：{'、'.join(tags)}"
        type_text = {"prospective": "准客户", "active": "活跃客户", "lapsed": "流失客户"}.get(customer["customer_type"], "")
        profile += f"。当前为{type_text}，处于{customer['current_stage']}阶段"
        if notes:
            profile += f"。{notes}"

        return {
            "customer_profile": profile,
            "purchase_intent": purchase_intent,
            "price_sensitivity": price_sensitivity,
            "recommended_products": recommended[:5],
            "recommended_actions": actions,
            "forbidden_actions": forbidden,
            "risk_notes": risks,
        }

    def _get_demo_analysis(self, customer: dict) -> str:
        """生成演示模式的 AI 分析文本。"""
        structured = self._generate_structured_analysis(customer)
        parts = [
            f"## AI分析 - 客户画像\n{structured['customer_profile']}",
            f"## AI分析 - 购买意向评分\n{structured['purchase_intent']}/10",
            f"## AI分析 - 价格敏感度\n{structured['price_sensitivity']}",
            f"## AI分析 - 推荐产品\n" + "、".join(structured["recommended_products"]),
            f"## AI分析 - 建议行动\n" + "\n".join(f"- {a}" for a in structured["recommended_actions"]),
            f"## AI分析 - 禁忌事项\n" + "\n".join(f"- {a}" for a in structured["forbidden_actions"]),
            f"## AI分析 - 风险提示\n" + "\n".join(f"- {r}" for r in structured["risk_notes"]),
        ]
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _customer_to_dict(customer) -> dict:
        """将 Customer ORM 对象转为字典。"""
        return {
            "id": str(customer.id),
            "name": customer.name,
            "age": customer.age,
            "gender": customer.gender,
            "phone": customer.phone,
            "customer_type": customer.customer_type,
            "tags": customer.tags,
            "insurance_type": customer.insurance_type,
            "current_stage": customer.current_stage,
            "intention_level": customer.intention_level,
            "source_channel": customer.source_channel,
            "notes": customer.notes,
            "assigned_to": str(customer.assigned_to) if customer.assigned_to else None,
            "organization_id": str(customer.organization_id),
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
        }

    @staticmethod
    def _customer_detail_to_dict(customer) -> dict:
        """将 Customer ORM 对象转为详情字典（含互动和跟进）。"""
        data = CustomerService._customer_to_dict(customer)
        data["interactions"] = [
            {
                "id": str(i.id),
                "customer_id": str(i.customer_id),
                "type": i.type,
                "direction": i.direction,
                "content": i.content,
                "outcome": i.outcome,
                "next_followup_date": i.next_followup_date.isoformat() if i.next_followup_date else None,
                "created_at": i.created_at.isoformat(),
            }
            for i in (customer.interactions or [])
        ]
        data["followups"] = [
            {
                "id": str(f.id),
                "customer_id": str(f.customer_id),
                "scheduled_date": f.scheduled_date.isoformat(),
                "completed_date": f.completed_date.isoformat() if f.completed_date else None,
                "status": f.status,
                "content": f.content,
                "result": f.result,
                "created_at": f.created_at.isoformat(),
            }
            for f in (customer.followups or [])
        ]
        return data
