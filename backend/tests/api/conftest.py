"""API 测试公共 fixtures。"""
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def sample_customer_data():
    """示例客户创建数据。"""
    return {
        "name": "测试客户",
        "age": 35,
        "gender": "male",
        "phone": "13900139000",
        "type": "active",
        "insurance_type": "medical",
        "stage": "needs_analysis",
        "intention_level": 3,
        "source": "referral",
        "tags": ["VIP"],
        "remark": "自动化测试创建"
    }
