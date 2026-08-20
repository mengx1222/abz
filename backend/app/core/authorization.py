"""数据级权限工具 —— 行级权限检查（IDOR防护）。

提供 DataPermissionChecker 类用于在 Service 层进行数据权限过滤，
以及 require_data_permission FastAPI 依赖工厂用于在路由层进行 IDOR 防护。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.user import User

try:
    from structlog import get_logger
    logger = get_logger()
except ImportError:
    logger = None  # type: ignore[assignment]

# 角色层级（从高到低）
_ROLE_HIERARCHY: dict[str, int] = {
    "SYSTEM_ADMIN": 100,
    "HQ_ADMIN": 80,
    "BRANCH_ADMIN": 60,
    "TEAM_LEADER": 40,
    "AGENT": 20,
}


class DataPermissionChecker:
    """基于当前用户角色的数据级权限检查器。

    用于 Service 层对业务数据进行行级权限过滤，防止 IDOR（越权访问）。

    支持的角色权限模型：
    - SYSTEM_ADMIN: 可访问所有数据
    - HQ_ADMIN: 可访问本机构及下属机构的数据
    - BRANCH_ADMIN: 可访问本机构及下属机构的数据
    - TEAM_LEADER: 可访问本团队的数据
    - AGENT: 仅可访问自己的数据（Demo 模式下放宽为同机构）
    """

    def __init__(self, current_user: User) -> None:
        self._user = current_user
        self._role_code: str = current_user.role_code
        self._org_id: str = str(current_user.organization_id)
        self._team_id: str | None = (
            str(current_user.team_id) if current_user.team_id else None
        )
        # ULTIMATE Pilot：demo 宽松分支仅在「环境是 demo 且用户是 demo 用户」时生效。
        # 此前仅看 user.demo_mode —— production 环境（DEMO_MODE=false）下 seed 演示用户
        # 登录会被误判为 demo 用户 → 绕过 P0-1 assigned 隔离（同 org 全可见）。
        self._is_demo: bool = settings.DEMO_MODE and getattr(current_user, "demo_mode", False)
        self._user_id: str = str(current_user.id)

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def can_access_customer(
        self, customer_org_id: str | None, assigned_to: str | None = None
    ) -> bool:
        """判断当前用户是否有权访问指定客户数据。

        Args:
            customer_org_id: 目标客户所属的 organization_id。
            assigned_to: 目标客户的 assigned_to（归属用户 ID）。
                生产模式 AGENT 依赖该字段判定归属（与列表过滤同源）。

        Returns:
            True 表示允许访问。
        """
        if customer_org_id is None:
            # 无组织归属的数据，仅系统管理员可访问
            return self._role_code == "SYSTEM_ADMIN"

        if self._role_code == "SYSTEM_ADMIN":
            return True

        if self._role_code in ("HQ_ADMIN", "BRANCH_ADMIN"):
            accessible = self.filter_accessible_org_ids()
            return customer_org_id in accessible

        if self._role_code == "TEAM_LEADER":
            accessible = self.filter_accessible_org_ids()
            return customer_org_id in accessible

        # AGENT 及其他角色
        if self._is_demo:
            # Demo 模式放宽限制：允许 AGENT 查看同 organization_id 的所有客户
            return customer_org_id == self._org_id

        # 正式模式（Task 44 P0-1）：仅可访问自己 assigned 的客户（兼验组织匹配），
        # 与列表过滤 restrict_to_own_customers 同一谓词来源，杜绝列表/详情判定不同源。
        if self._role_code == "AGENT":
            return (
                assigned_to is not None
                and str(assigned_to) == self._user_id
                and customer_org_id == self._org_id
            )

        return False

    def can_access_document(self, document_org_id: str | None) -> bool:
        """判断当前用户是否有权访问指定 organization_id 的知识库文档。

        逻辑与 can_access_customer 一致，但用于知识库文档资源。

        Args:
            document_org_id: 目标文档所属的 organization_id。

        Returns:
            True 表示允许访问。
        """
        # 文档权限与客户权限使用相同逻辑
        return self.can_access_customer(document_org_id)

    def can_manage_user(self, target_user: User) -> bool:
        """判断当前用户是否有权管理目标用户。

        规则：
        - 不能管理自己
        - 只能管理同机构或下属机构的用户
        - 角色层级不低于目标用户

        Args:
            target_user: 被管理的目标用户。

        Returns:
            True 表示允许管理。
        """
        # 不能管理自己
        if target_user.id == self._user.id:
            return False

        # 系统管理员可以管理所有人
        if self._role_code == "SYSTEM_ADMIN":
            return True

        my_level = _ROLE_HIERARCHY.get(self._role_code, 0)
        target_level = _ROLE_HIERARCHY.get(target_user.role_code, 0)

        # 角色层级不能低于目标
        if my_level <= target_level:
            return False

        # 只能管理同机构或下属机构的用户
        target_org_id = str(target_user.organization_id)
        accessible = self.filter_accessible_org_ids()
        return target_org_id in accessible

    def filter_accessible_org_ids(self) -> list[str]:
        """返回当前用户可访问的所有 organization_id 列表。

        用于数据库查询 WHERE 条件，例如：
            ``query.where(Customer.organization_id.in_(accessible_org_ids))``

        Returns:
            可访问的 organization_id 字符串列表。
        """
        if self._role_code == "SYSTEM_ADMIN":
            # 系统管理员返回特殊标记，调用方应跳过 org 过滤
            return ["__ALL__"]

        if self._role_code in ("HQ_ADMIN", "BRANCH_ADMIN"):
            # 总部/分公司管理员：本机构 + 所有下属机构
            org_ids = self._collect_child_org_ids(self._org_id)
            return org_ids

        if self._role_code == "TEAM_LEADER":
            # 团队长：本团队 + 下属团队
            org_ids = [self._org_id]
            if self._team_id:
                child_ids = self._collect_child_org_ids(self._team_id)
                org_ids.extend(child_ids)
            return list(dict.fromkeys(org_ids))  # 去重保序

        # AGENT 及其他角色
        if self._is_demo:
            # Demo 模式放宽：同机构的客户都可见
            return [self._org_id]

        # 正式模式：仅返回自己的组织 ID（实际还需配合 assigned_to 过滤）
        return [self._org_id]

    def restrict_to_own_customers(self) -> bool:
        """生产模式 AGENT：客户数据仅限本人 assigned（列表过滤谓词）。

        与 can_access_customer 的 AGENT 分支同源：列表加 ``assigned_to == user.id``
        WHERE 条件，详情判定同一谓词，保证列表/详情行为一致。
        """
        return (not self._is_demo) and self._role_code == "AGENT"

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _collect_child_org_ids(self, root_org_id: str) -> list[str]:
        """递归收集某组织及其所有子组织的 ID。

        在 demo 模式下，由于没有真实数据库连接，
        只返回当前组织 ID 本身。

        在正式模式下，应该通过数据库查询组织树。
        此处提供一个基础实现，后续可通过依赖注入增强。
        """
        if self._is_demo or settings.DEMO_MODE:
            # Demo 模式下无法查询组织树，返回当前组织
            return [root_org_id]

        # 正式模式：尝试从用户的 organization 关系获取子组织
        org_ids = [root_org_id]
        try:
            org = self._user.organization
            if org and hasattr(org, "children") and org.children:
                self._walk_org_tree(org.children, org_ids)
        except Exception:
            if logger:
                logger.warning(
                    "failed_to_collect_child_orgs",
                    root_org_id=root_org_id,
                )
        return org_ids

    @staticmethod
    def _walk_org_tree(children: list, org_ids: list[str]) -> None:
        """递归遍历组织树，收集所有子组织 ID。"""
        for child in children:
            org_ids.append(str(child.id))
            if hasattr(child, "children") and child.children:
                DataPermissionChecker._walk_org_tree(child.children, org_ids)


# ------------------------------------------------------------------
# FastAPI 依赖工厂
# ------------------------------------------------------------------

def require_data_permission(resource_type: str):
    """FastAPI 依赖工厂：检查当前用户是否有权访问请求的资源。

    用法示例::

        @router.get("/customers/{customer_id}")
        async def get_customer(
            customer_id: uuid.UUID,
            _: None = Depends(require_data_permission("customer")),
            current_user: User = Depends(get_current_user),
        ):
            ...

    Args:
        resource_type: 资源类型，目前支持 ``"customer"`` 和 ``"document"``。

    Returns:
        FastAPI 依赖函数。
    """

    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> None:
        checker = DataPermissionChecker(current_user)

        # require_data_permission 主要作为路由级守卫使用
        # 细粒度的资源 ID 检查在 Service 层通过 DataPermissionChecker 完成
        # 此处做基础的角色验证
        accessible = checker.filter_accessible_org_ids()

        if not accessible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"当前角色 ({current_user.role_code}) 无权访问 {resource_type} 数据",
                },
            )

    return _check
