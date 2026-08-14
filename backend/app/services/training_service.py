"""AI 陪练服务 —— 管理训练场景、会话、AI 客户角色扮演与教练辅导。

演示模式使用内存数据，包含 23 个预设场景。
"""
import json
import uuid
import random
from collections.abc import AsyncGenerator
from datetime import datetime, timezone, timedelta

from structlog import get_logger

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import get_ai_gateway
from app.core.config import settings
from app.repositories.training_repo import TrainingScenarioRepository, TrainingSessionRepository

logger = get_logger()

# ==================================================================
# Demo scenario data (23 scenarios)
# ==================================================================

_DEMO_SCENARIOS: list[dict] = [
    # ---- 价格异议类 (Price Objections) ----
    {
        "id": "s-price-001",
        "title": "\"太贵了\" — 重疾险价格犹豫",
        "description": "中年客户对重疾险的年缴保费感到犹豫，认为保费太高，需要你化解价格异议并传达产品价值。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "王建国",
            "age": 45,
            "personality": "务实谨慎，善于算账，不容易被说服",
            "mood": "犹豫不决，有些防备",
            "background": "私企中层管理，家庭年收入40万，房贷每月1.5万，女儿刚上高中",
            "insurance_knowledge": "对保险有基本了解，觉得社保够了，之前没买过商业保险",
            "key_objections": ["太贵了，一年要一万多", "我有医保，生病也能报销", "万一没出事钱就白花了", "等我再考虑考虑"]
        },
        "product_focus": "重疾险",
        "sales_stage": "异议处理",
        "evaluation_criteria": {
            "product_accuracy": "是否准确说明重疾险与医疗险的区别、保费计算逻辑",
            "empathy": "是否理解客户经济压力，以共情方式切入",
            "closing_action": "是否提出具体方案（如调整保额、缴费期），推动下一步"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "价格异议类",
    },
    {
        "id": "s-price-002",
        "title": "\"网上更便宜\" — 互联网保险对比",
        "description": "年轻客户在网上看到更便宜的保险产品，质疑线下产品价格。需要你说明线下服务的价值差异。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "李思琪",
            "age": 28,
            "personality": "互联网原住民，喜欢自己做研究，自信且理性",
            "mood": "好奇但带有挑战性",
            "background": "互联网公司产品经理，年薪25万，单身，注重性价比",
            "insurance_knowledge": "在网上研究过不少保险产品，对条款有基本理解",
            "key_objections": ["网上那个才2000块，你们要5000", "条款都差不多吧", "理赔还不是自己在线操作", "我感觉买线下的不值"]
        },
        "product_focus": "重疾险",
        "sales_stage": "异议处理",
        "evaluation_criteria": {
            "product_accuracy": "能否指出线上/线下产品的实际差异（保障责任、理赔服务、健康告知）",
            "empathy": "是否认可客户的比较行为，不贬低竞品",
            "closing_action": "是否引导客户关注服务价值而非纯价格"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "价格异议类",
    },
    {
        "id": "s-price-003",
        "title": "\"没必要买\" — 社保足够论",
        "description": "客户认为已有社保，不需要再买商业保险。需要你让客户认识到社保的局限性和商业保险的补充作用。",
        "difficulty": "easy",
        "customer_persona": {
            "name": "张磊",
            "age": 35,
            "personality": "性格直爽，对保险不太感冒，认为多余",
            "mood": "有些不耐烦，觉得被推销",
            "background": "国企员工，工作稳定，有五险一金，妻子刚生二胎",
            "insurance_knowledge": "只知道有医保，不了解商业保险的具体作用",
            "key_objections": ["我有医保，看病能报销", "单位都给交了社保", "商业保险都是骗人的", "我不想花这个冤枉钱"]
        },
        "product_focus": "医疗险",
        "sales_stage": "需求唤醒",
        "evaluation_criteria": {
            "product_accuracy": "能否清晰说明社保报销比例限制、自费药不报等关键点",
            "empathy": "不否定客户的想法，用事实引导",
            "closing_action": "能否用一个具体案例让客户产生危机意识"
        },
        "duration_minutes": 8,
        "is_active": True,
        "category": "价格异议类",
    },
    {
        "id": "s-price-004",
        "title": "\"考虑一下\" — 拖延决策",
        "description": "客户总是说\"考虑一下\"，多次沟通仍未决策。需要你识别拖延背后的真实原因并推动成交。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "陈雅婷",
            "age": 38,
            "personality": "优柔寡断，怕做错决定，需要充分安全感",
            "mood": "礼貌但保持距离",
            "background": "银行职员，年收入18万，已婚有一子，之前咨询过三次",
            "insurance_knowledge": "对保险有一定了解，但总担心买错",
            "key_objections": ["我再考虑考虑吧", "我跟家人商量一下", "我再对比对比", "下次再说吧"]
        },
        "product_focus": "重疾险",
        "sales_stage": "促成阶段",
        "evaluation_criteria": {
            "product_accuracy": "能否针对客户纠结的具体点给予专业解答",
            "empathy": "理解客户的决策压力，给予情感支持",
            "closing_action": "能否使用假设成交法、限时优惠等技巧推动决策"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "价格异议类",
    },
    {
        "id": "s-price-005",
        "title": "\"先不买\" — 明确拒绝",
        "description": "客户明确表示现在不想买保险，但分析后发现其实有保障需求。需要你在尊重客户的同时留下机会。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "刘志强",
            "age": 42,
            "personality": "固执，不喜欢被推销，但内心有家庭责任感",
            "mood": "有些不耐烦，但不会直接翻脸",
            "background": "建筑公司项目经理，家庭年收入50万，有两个孩子，父母身体不好",
            "insurance_knowledge": "对保险印象一般，觉得理赔难",
            "key_objections": ["现在不想买", "没钱买保险", "保险买了也赔不到", "你加我微信吧以后再说"]
        },
        "product_focus": "综合保障",
        "sales_stage": "初次接触",
        "evaluation_criteria": {
            "product_accuracy": "能否简明扼要说明保险的核心价值",
            "empathy": "不纠缠客户，体现专业素养",
            "closing_action": "能否成功留下联系方式或预约下次沟通"
        },
        "duration_minutes": 8,
        "is_active": True,
        "category": "价格异议类",
    },
    # ---- 需求认知类 (Need Awareness) ----
    {
        "id": "s-need-001",
        "title": "\"身体挺好不需要保险\" — 缺乏风险意识",
        "description": "年轻健康客户认为自己身体好，不需要保险。需要你帮助建立风险意识。",
        "difficulty": "easy",
        "customer_persona": {
            "name": "赵阳",
            "age": 26,
            "personality": "乐观自信，觉得年轻就是资本",
            "mood": "轻松随意，不以为然",
            "background": "程序员，年薪30万，经常加班，单身，父母有退休金",
            "insurance_knowledge": "几乎为零，觉得保险是老年人需要的",
            "key_objections": ["我才26岁，身体好着呢", "保险是老年人才需要的吧", "等我老了再买不行吗", "年轻人买保险是不是太早了"]
        },
        "product_focus": "重疾险",
        "sales_stage": "需求唤醒",
        "evaluation_criteria": {
            "product_accuracy": "能否说明年轻买保险的优势（保费低、健康门槛低）",
            "empathy": "用贴近年轻人生活的语言沟通",
            "closing_action": "能否用数据或案例让客户重视起来"
        },
        "duration_minutes": 8,
        "is_active": True,
        "category": "需求认知类",
    },
    {
        "id": "s-need-002",
        "title": "\"以前买过保险被骗了\" — 负面保险经验",
        "description": "客户有过不愉快的保险经历，对保险行业不信任。需要你重建信任。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "孙秀英",
            "age": 50,
            "personality": "谨慎多疑，一旦形成看法很难改变",
            "mood": "抵触情绪较强，但愿意听你说完",
            "background": "退休教师，丈夫三年前因病去世，之前买过分红险觉得被骗",
            "insurance_knowledge": "有购买经验，但对保险产品理解片面",
            "key_objections": ["上次买的分红险根本没分红", "你们保险都是忽悠人的", "理赔的时候这也不赔那也不赔", "我怎么信得过你们"]
        },
        "product_focus": "医疗险",
        "sales_stage": "信任重建",
        "evaluation_criteria": {
            "product_accuracy": "能否准确区分不同产品类型，说明之前产品的实际情况",
            "empathy": "充分共情客户的负面经历，不回避问题",
            "closing_action": "能否以退为进，先建立关系再谈业务"
        },
        "duration_minutes": 15,
        "is_active": True,
        "category": "需求认知类",
    },
    {
        "id": "s-need-003",
        "title": "\"我有社保了\" — 社保万能论",
        "description": "客户认为社保已经足够覆盖所有医疗费用。需要你系统说明社保的保障边界。",
        "difficulty": "easy",
        "customer_persona": {
            "name": "周敏",
            "age": 33,
            "personality": "理性温和，愿意了解但需要逻辑说服",
            "mood": "平静开放",
            "background": "公务员，工作稳定，有完善的医保和公积金，已婚",
            "insurance_knowledge": "知道社保能报销大部分，不了解具体比例和封顶线",
            "key_objections": ["我们单位医保很好的", "大病也有大病医保", "我觉得社保够用了", "商业保险是多此一举"]
        },
        "product_focus": "医疗险",
        "sales_stage": "需求唤醒",
        "evaluation_criteria": {
            "product_accuracy": "能否清晰说明社保的起付线、封顶线、自费药等限制",
            "empathy": "肯定社保的价值，在认同基础上补充",
            "closing_action": "能否用具体数字说明社保与商业保险的互补关系"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "需求认知类",
    },
    {
        "id": "s-need-004",
        "title": "\"买了保险也没用\" — 对保险效果存疑",
        "description": "客户听说了各种保险不理赔的案例，对保险的实际效果存疑。需要你用事实消除疑虑。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "吴昊天",
            "age": 40,
            "personality": "批判性思维强，喜欢找反面例子",
            "mood": "质疑态度明显，但并非完全拒绝",
            "background": "律师，年收入60万，理性思维，经常看到保险纠纷案例",
            "insurance_knowledge": "对保险合同和理赔条款有一定了解",
            "key_objections": ["我看过很多理赔被拒的案例", "健康告知那么严格，稍有不慎就不赔", "条款全是霸王条款", "真的出事了能不能赔还是个问题"]
        },
        "product_focus": "重疾险",
        "sales_stage": "异议处理",
        "evaluation_criteria": {
            "product_accuracy": "能否从专业角度解释理赔流程和拒赔常见原因",
            "empathy": "认可客户的担忧，不回避行业问题",
            "closing_action": "能否用华安理赔数据和案例增强说服力"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "需求认知类",
    },
    # ---- 慢病客户类 (Chronic Disease) ----
    {
        "id": "s-chronic-001",
        "title": "\"有高血压能买吗\" — 慢病客户投保",
        "description": "客户有高血压，担心无法购买保险。需要你说明慢病客户的投保选项和健康告知要点。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "马德福",
            "age": 52,
            "personality": "焦虑型，对自己的健康状况很担心",
            "mood": "焦虑期待，希望有解决方案",
            "background": "餐饮店老板，有高血压3年，每天服药控制，BMI偏高",
            "insurance_knowledge": "知道有健康告知，但不清楚具体怎么填",
            "key_objections": ["我有高血压能买吗", "买了会不会不赔", "要不要告知高血压", "保费会不会很贵"]
        },
        "product_focus": "医疗险",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否准确说明高血压的投保条件、智能核保流程",
            "empathy": "理解客户对健康的担忧，给予安心感",
            "closing_action": "能否引导客户进行智能核保测试，明确可投保产品"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "慢病客户类",
    },
    {
        "id": "s-chronic-002",
        "title": "\"糖尿病客户\" — 糖尿病投保咨询",
        "description": "客户被诊断为2型糖尿病，想了解还能买什么保险。需要你提供专业指导。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "黄丽华",
            "age": 48,
            "personality": "注重健康管理，积极乐观但现实",
            "mood": "期待找到解决方案，有点失落",
            "background": "会计，2型糖尿病2年，血糖控制尚可，有家族糖尿病史",
            "insurance_knowledge": "了解一些保险知识，知道糖尿病投保困难",
            "key_objections": ["听说糖尿病买不了重疾险", "有没有专门给糖尿病患者的保险", "我这种情况还能买什么", "保费会不会因为糖尿病涨很多"]
        },
        "product_focus": "医疗险",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否准确说明糖尿病可投保的产品类型和条件",
            "empathy": "给予客户希望和专业指导",
            "closing_action": "能否提供可行的替代方案"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "慢病客户类",
    },
    {
        "id": "s-chronic-003",
        "title": "\"体检有异常\" — 体检指标异常",
        "description": "客户最近体检发现甲状腺结节等问题，担心影响投保。需要你指导如何处理。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "林小芳",
            "age": 32,
            "personality": "细心谨慎，容易紧张",
            "mood": "紧张担忧",
            "background": "外企HR，年度体检发现甲状腺结节2级，其他指标正常",
            "insurance_knowledge": "对保险了解不多，刚意识到需要买",
            "key_objections": ["甲状腺结节影响买保险吗", "体检异常是不是就不能买了", "如果被拒保了怎么办", "要不要先治好再买"]
        },
        "product_focus": "重疾险",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否准确说明甲状腺结节的核保标准（分级不同结果不同）",
            "empathy": "安抚客户情绪，说明体检异常很常见",
            "closing_action": "能否引导客户先尝试智能核保"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "慢病客户类",
    },
    # ---- 老年客户类 (Elderly) ----
    {
        "id": "s-elderly-001",
        "title": "\"超过60岁能买什么\" — 老年客户投保限制",
        "description": "60岁以上客户想买保险但面临年龄限制。需要你推荐适合老年客户的产品方案。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "杨大爷",
            "age": 63,
            "personality": "节俭朴实，不想给儿女添负担",
            "mood": "诚恳谦虚",
            "background": "退休工人，有退休金4000/月，老伴也退休了，有一个儿子",
            "insurance_knowledge": "几乎不懂保险，是听邻居说才来问问",
            "key_objections": ["我都60多了还能买吗", "别太贵的，我退休金不多", "会不会体检过不了", "我儿子说保险都是骗老人的"]
        },
        "product_focus": "意外险",
        "sales_stage": "需求分析",
        "evaluation_criteria": {
            "product_accuracy": "能否推荐适合老年人的产品（防癌险、意外险、惠民保）",
            "empathy": "尊重老年客户，耐心讲解，避免专业术语",
            "closing_action": "能否给出一个 affordable 的方案让客户接受"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "老年客户类",
    },
    {
        "id": "s-elderly-002",
        "title": "\"给父母买\" — 子女为父母投保",
        "description": "年轻客户想给年迈的父母买保险。需要你分析老年人投保的限制并推荐可行方案。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "何晓东",
            "age": 30,
            "personality": "孝顺负责，有保险意识",
            "mood": "积极认真",
            "background": "IT工程师，父母都60岁以上，父亲有高血压，母亲身体健康",
            "insurance_knowledge": "自己买过保险，但对老年人投保不了解",
            "key_objections": ["父母年纪大了还能买什么", "父亲有高血压会不会被拒", "有没有不用体检的保险", "想给父母都买上大概要多少钱"]
        },
        "product_focus": "综合保障",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否分别给出父母二人的投保方案",
            "empathy": "肯定客户的孝心，理解担忧",
            "closing_action": "能否提供清晰的方案对比和预算建议"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "老年客户类",
    },
    {
        "id": "s-elderly-003",
        "title": "\"退休了需要什么保险\" — 退休保障规划",
        "description": "即将退休或刚退休的客户，需要了解退休后的保险规划。需要你提供全面的保障建议。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "郑国平",
            "age": 58,
            "personality": "退休前是管理层，有规划意识，注重品质",
            "mood": "从容理性",
            "background": "即将从国企退休，退休金约8000/月，有存款200万，妻子56岁",
            "insurance_knowledge": "之前公司有团体险，退休后就没有了",
            "key_objections": ["退休后原来的团险就没了", "这个年纪买什么比较合适", "有没有那种能领钱的保险", "我不想体检太麻烦"]
        },
        "product_focus": "年金险",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否说明退休后保险配置的优先级（意外>医疗>年金）",
            "empathy": "理解客户对退休生活品质的追求",
            "closing_action": "能否给出一个分步实施的建议"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "老年客户类",
    },
    # ---- 家庭客户类 (Family) ----
    {
        "id": "s-family-001",
        "title": "\"一家三口怎么买\" — 家庭保障方案",
        "description": "客户想给一家三口配置保险。需要你设计合理的家庭保障方案。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "钱伟明",
            "age": 36,
            "personality": "家庭责任感强，做事有规划",
            "mood": "认真考虑中",
            "background": "IT公司技术总监，年薪50万，妻子全职带娃，儿子3岁，有房贷200万",
            "insurance_knowledge": "知道应该买保险，但不知道怎么配置",
            "key_objections": ["一家三口买什么合适", "保费预算大概多少合理", "先给谁买比较重要", "能不能给我做一个方案"]
        },
        "product_focus": "综合保障",
        "sales_stage": "方案设计",
        "evaluation_criteria": {
            "product_accuracy": "能否按先大人后小孩的原则设计方案",
            "empathy": "理解家庭经济压力，给出合理的预算建议",
            "closing_action": "能否提供结构化的家庭保障方案"
        },
        "duration_minutes": 15,
        "is_active": True,
        "category": "家庭客户类",
    },
    {
        "id": "s-family-002",
        "title": "\"孩子刚出生\" — 新生儿保险规划",
        "description": "新手父母想给刚出生的宝宝买保险。需要你指导新生儿保险配置。",
        "difficulty": "easy",
        "customer_persona": {
            "name": "冯雪梅",
            "age": 29,
            "personality": "新手妈妈，焦虑型，想把最好的给孩子",
            "mood": "充满期待但有点焦虑",
            "background": "小学老师，宝宝刚满月，丈夫是公务员，家庭年收入20万",
            "insurance_knowledge": "了解少儿医保，不太了解商业保险",
            "key_objections": ["新生儿买什么保险好", "有没有必要买教育金", "宝宝那么小需要买重疾险吗", "我预算不多大概5000以内"]
        },
        "product_focus": "少儿重疾险",
        "sales_stage": "需求分析",
        "evaluation_criteria": {
            "product_accuracy": "能否说明新生儿保险配置的优先级",
            "empathy": "理解新手妈妈的焦虑，给予温暖专业的建议",
            "closing_action": "能否在预算内给出合理的配置建议"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "家庭客户类",
    },
    {
        "id": "s-family-003",
        "title": "\"房贷压力大\" — 经济支柱保障",
        "description": "客户房贷压力大，担心万一出事家人还不起房贷。需要你帮助客户认识到保障的紧迫性。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "许大鹏",
            "age": 39,
            "personality": "压力大但不爱表露，习惯自己扛",
            "mood": "疲惫但强撑",
            "background": "销售经理，家庭年收入35万，房贷每月2万（剩余20年），两个孩子",
            "insurance_knowledge": "知道应该买保险，但觉得保费负担重",
            "key_objections": ["每个月房贷2万，哪有钱买保险", "定期寿险是什么", "万一我出事了保险能帮到什么", "保费最好控制在3000以内"]
        },
        "product_focus": "定期寿险",
        "sales_stage": "需求唤醒",
        "evaluation_criteria": {
            "product_accuracy": "能否准确说明定期寿险对房贷家庭的意义",
            "empathy": "理解客户的经济压力，不道德绑架",
            "closing_action": "能否用低保费高保额的方案打动客户"
        },
        "duration_minutes": 12,
        "is_active": True,
        "category": "家庭客户类",
    },
    # ---- 高净值客户类 (HNW) ----
    {
        "id": "s-hnw-001",
        "title": "\"我有不少存款\" — 高净值客户资产配置",
        "description": "高净值客户认为存款足够，不需要保险。需要你从资产配置和财富传承角度切入。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "沈董事长",
            "age": 55,
            "personality": "自信强势，见过世面，不容易被说服",
            "mood": "礼貌但有距离感",
            "background": "制造业企业主，资产过亿，有两套房，一个儿子在国外留学",
            "insurance_knowledge": "对保险不感兴趣，觉得收益率太低",
            "key_objections": ["我存银行也有利息，何必买保险", "保险收益太低了", "我有钱还需要保险吗", "年金险那点收益我看不上"]
        },
        "product_focus": "年金险",
        "sales_stage": "需求唤醒",
        "evaluation_criteria": {
            "product_accuracy": "能否从资产隔离、税务筹划、财富传承角度说明保险价值",
            "empathy": "尊重客户的成功，用对等的身份沟通",
            "closing_action": "能否引发客户对资产保全的思考"
        },
        "duration_minutes": 15,
        "is_active": True,
        "category": "高净值客户类",
    },
    {
        "id": "s-hnw-002",
        "title": "\"企业主\" — 企业主保障需求",
        "description": "企业主需要个人和企业的综合保障方案。需要你理解企业主的特殊需求。",
        "difficulty": "hard",
        "customer_persona": {
            "name": "曹总",
            "age": 48,
            "personality": "精明务实，看重效率，讨厌浪费时间",
            "mood": "忙碌但愿意听有用的信息",
            "background": "贸易公司老板，公司年营收5000万，妻子管财务，一儿一女",
            "insurance_knowledge": "公司给员工买了团险，个人没怎么配置",
            "key_objections": ["我很忙，你有话直说", "我需要的不是普通的那种", "企业风险和个人风险怎么分开", "有没有高端医疗那种"]
        },
        "product_focus": "综合保障",
        "sales_stage": "需求分析",
        "evaluation_criteria": {
            "product_accuracy": "能否提供企业主专属的保障方案（家企隔离、高端医疗、团险）",
            "empathy": "理解企业主的忙碌，高效沟通",
            "closing_action": "能否快速建立专业形象并预约深入沟通"
        },
        "duration_minutes": 15,
        "is_active": True,
        "category": "高净值客户类",
    },
    # ---- 销售技巧类 (Sales Skills) ----
    {
        "id": "s-skill-001",
        "title": "\"如何在朋友圈发保险\" — 社交媒体营销",
        "description": "新入行的代理人不知道如何在朋友圈进行有效的保险营销。需要你指导社交媒体技巧。",
        "difficulty": "easy",
        "customer_persona": {
            "name": "小张",
            "age": 25,
            "personality": "热情积极，刚入行，缺乏经验",
            "mood": "求知欲强，有点迷茫",
            "background": "应届毕业生，刚入行保险3个月，朋友圈基本都是同龄人",
            "insurance_knowledge": "产品知识还在学习中",
            "key_objections": ["我发朋友圈没人点赞", "朋友说我变了", "不知道发什么内容好", "怕被屏蔽"]
        },
        "product_focus": "社交媒体营销",
        "sales_stage": "获客技巧",
        "evaluation_criteria": {
            "product_accuracy": "能否给出具体的朋友圈内容策略和发布技巧",
            "empathy": "理解新人的困惑，给予鼓励",
            "closing_action": "能否提供可执行的30天内容计划"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "销售技巧类",
    },
    {
        "id": "s-skill-002",
        "title": "\"被拒绝后如何跟进\" — 异议处理",
        "description": "代理人遇到客户拒绝后不知道如何跟进。场景模拟客户拒绝后的再次接触。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "田姐",
            "age": 37,
            "personality": "外冷内热，需要时间建立信任",
            "mood": "有些意外你还会联系",
            "background": "美容店老板，半年前拒绝过你的推销，最近听说朋友生病了",
            "insurance_knowledge": "之前不太在意，现在开始有所动摇",
            "key_objections": ["上次不是说了不需要吗", "你怎么又来了", "我真的没时间", "你先发资料我看看吧"]
        },
        "product_focus": "重疾险",
        "sales_stage": "跟进回访",
        "evaluation_criteria": {
            "product_accuracy": "能否选择合适的跟进理由和话术",
            "empathy": "不给客户压力，以关心而非推销的方式接触",
            "closing_action": "能否打开话题并预约面谈"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "销售技巧类",
    },
    {
        "id": "s-skill-003",
        "title": "\"转介绍话术\" — 老客户推荐",
        "description": "想请满意的老客户帮忙转介绍。需要你练习转介绍的沟通技巧。",
        "difficulty": "medium",
        "customer_persona": {
            "name": "郑哥",
            "age": 45,
            "personality": "热心但谨慎，不轻易帮人推荐",
            "mood": "友好但有所保留",
            "background": "老客户，去年买了全家保险，理赔体验很好，对你比较信任",
            "insurance_knowledge": "对华安的产品和服务比较满意",
            "key_objections": ["推荐给别人万一不合适怎么办", "我朋友好像不太需要", "我不太擅长帮人介绍", "你直接跟我说要推荐什么样的人吧"]
        },
        "product_focus": "转介绍技巧",
        "sales_stage": "老客户经营",
        "evaluation_criteria": {
            "product_accuracy": "能否说明转介绍的正确方式和时机",
            "empathy": "理解客户的顾虑，不给压力",
            "closing_action": "能否获得具体的转介绍线索"
        },
        "duration_minutes": 10,
        "is_active": True,
        "category": "销售技巧类",
    },
]

# ==================================================================
# Demo coaching hints keyed by coaching category
# ==================================================================

_COACHING_HINTS: dict[str, list[str]] = {
    "empathy": [
        "💡 尝试先认同客户的感受，再进行引导",
        "💡 注意倾听客户的深层需求，不要急于推销产品",
        "💡 可以用\"我理解您的顾虑\"开头来建立共情",
        "💡 客户的异议背后往往有真实的需求，试着挖掘",
        "💡 适当分享类似客户的经历，让客户感到被理解",
    ],
    "product": [
        "💡 回答产品信息时，注意结合客户的具体情况",
        "💡 可以用对比的方式帮助客户理解产品差异",
        "💡 提到具体数字时确保准确，增强专业可信度",
        "💡 尝试用生活化的比喻解释专业概念",
        "💡 介绍产品时先说能解决客户什么问题，再说产品特点",
    ],
    "closing": [
        "💡 当前是一个推动决策的好时机，可以尝试提出具体方案",
        "💡 可以使用二选一法帮助客户做决定",
        "💡 适时营造紧迫感，但要避免让客户感到压力",
        "💡 给客户一个明确的下一步动作，比如\"我们先做个方案看看\"",
        "💡 确认客户的核心顾虑已经解决后再推进成交",
    ],
}

# ==================================================================
# Demo customer responses keyed by scenario category + turn
# ==================================================================

_DEMO_CUSTOMER_RESPONSES: dict[str, list[str]] = {
    # 价格异议类
    "s-price-001": [
        "你好，我之前在网上看到你们华安的重疾险，一年要一万多，说实话我觉得挺贵的。",
        "一万多一年，二十年就是二十多万，这钱存银行也有不少利息了吧？我总觉得不太划算。",
        "我倒是也知道保险有用，但是这个价格确实有点超出我的预算了。我房贷每个月就要一万五。",
        "嗯……你说的有道理，但是我还是觉得有点贵。有没有便宜一点的方案？",
        "我回去跟我老婆商量一下吧，你也别催我，我考虑考虑。",
    ],
    "s-price-002": [
        "我在网上看到某款重疾险，一年才两千多，保额也有50万。你们这个怎么要五千多？",
        "我觉得条款内容应该差不多吧？都是保重疾的，为什么要贵一倍多？",
        "理赔的话，网上买的也是在线提交资料吧？我不觉得线下有多方便。",
        "你说的线下服务具体是什么？我觉得我还是倾向性价比高一些的。",
        "嗯，你说的那些增值服务倒是挺不错的，我再对比对比吧。",
    ],
    "s-price-003": [
        "你好，我听你说保险，但我真的觉得没必要。我们单位医保都给交了，看病能报销。",
        "大病也有大病医保啊，我觉得够用了。花那钱干嘛？",
        "商业保险……说实话我一直觉得没什么用，是不是有病才用得上？",
        "你说的自费药那些确实我没想过，但我觉得概率不大吧。",
        "你说的那个百万医疗险多少钱一年？如果真的便宜的话可以了解一下。",
    ],
    "s-price-004": [
        "你好……嗯，你之前给我介绍过那个重疾险，我还在想。",
        "我不是不想买，就是觉得要做这个决定挺重大的，万一买错了呢？",
        "我老公说让我自己决定，但我总觉得要再看看。你们有没有什么优惠活动？",
        "其实我主要担心的是，万一以后交不起了怎么办？可以退吗？",
        "嗯……你说的分期缴费倒是个办法。我再仔细看看方案吧，你别着急。",
    ],
    "s-price-005": [
        "不好意思啊，我现在真的不想买保险。你不用给我介绍了。",
        "不是钱的问题，就是……算了，不说这个了。",
        "你们保险公司的人我见过不少了，每次都是那一套说辞。",
        "我现在很忙，真的没时间聊这个。你要是觉得合适就加个微信，以后有需要我找你吧。",
        "行吧，你加我微信，回头有空了我看看你朋友圈。别天天给我发消息就行。",
    ],
    # 需求认知类
    "s-need-001": [
        "保险？我这么年轻身体又好，买什么保险啊。",
        "哈哈，我觉得保险是老了才需要考虑的事吧，我现在才26。",
        "而且我天天运动，作息也规律，应该不会有什么大问题。",
        "你说的重疾年轻化……这个我倒是没想过。但我周围确实没听说谁这么年轻就生大病的。",
        "你说保费跟年龄有关？那倒是……年轻买确实便宜一些？给我算算多少钱？",
    ],
    "s-need-002": [
        "你又来推销保险？我跟你说过我之前被骗过。",
        "三年前我买了那个什么分红险，业务员说每年能分好多钱，结果呢？一年才分了几百块！",
        "我丈夫生病住院的时候，那个保险也没帮上什么忙。你们就知道收钱。",
        "你说你们华安不一样？我怎么知道你不是在忽悠我？",
        "……你说的我听进去了，但我现在确实不想做决定。你留个电话，我考虑考虑。",
    ],
    "s-need-003": [
        "我们公务员的医保很好的，看病基本都能报销。",
        "大病也有大病统筹啊，我觉得保障挺全面的了。",
        "你说的那个起付线和封顶线具体是多少？我不太了解这些细节。",
        "自费药不能报？这个我确实不知道。大概有多少药是自费的？",
        "嗯，你说的有道理。那你帮我看看有什么合适的，主要是补充社保那部分。",
    ],
    "s-need-004": [
        "我是做律师的，见过太多保险理赔纠纷了。老实说我对保险印象不太好。",
        "健康告知那些条款简直就是给保险公司留后路，稍微有点既往症就不赔。",
        "而且我看过很多拒赔案例，投保的时候什么都答应，理赔的时候各种理由。",
        "你说的理赔率数据是从哪来的？我需要看到具体数据才相信。",
        "嗯，你说的华安的理赔服务确实比我了解的要好一些。但你要理解我的职业习惯，我需要看具体的条款和案例。",
    ],
    # 慢病客户类
    "s-chronic-001": [
        "你好，我有个问题想问一下。我有高血压三年了，每天吃药控制，这种情况能买保险吗？",
        "那我投保的时候要不要告知我有高血压？如果告知了会不会被拒保？",
        "我血压控制在140/90左右，不算特别严重吧？",
        "你说的智能核保是什么意思？就是在手机上回答几个问题？",
        "如果能买的话，保费会不会比正常人贵很多？大概贵多少？",
    ],
    "s-chronic-002": [
        "你好，我被诊断了2型糖尿病，想了解一下还能买什么保险。",
        "我知道糖尿病买重疾险很难，但是医疗险呢？",
        "我的血糖控制得还可以，糖化血红蛋白在6.5左右。",
        "有没有专门针对糖尿病患者的保险产品？",
        "你说的那个惠民保确实可以买，但保障够不够？",
    ],
    "s-chronic-003": [
        "你好，我最近体检发现甲状腺结节，有点担心。",
        "体检报告上写的是甲状腺结节2级，医生说定期复查就行，但我担心买保险受影响。",
        "如果因为甲状腺结节被拒保了怎么办？会不会有记录影响以后买？",
        "你说的智能核保能直接出结果吗？不需要人工审核？",
        "如果能正常承保的话，那我想赶紧买一份，免得以后结节有变化。",
    ],
    # 老年客户类
    "s-elderly-001": [
        "小伙子，我听说你们这儿能买保险，我今年63了还能买不？",
        "我老伴也60多了，我们俩都想看看有没有什么合适的。",
        "别太贵的啊，我们两个加起来退休金才八千块钱。",
        "你说不用体检？那太好了，我这血压有点高，怕体检过不了。",
        "一年几百块钱的意外险？这个倒是可以考虑考虑。你给我详细说说。",
    ],
    "s-elderly-002": [
        "你好，我想给爸妈买点保险，但不知道他们这个年纪还能买什么。",
        "我爸60了有高血压，我妈58岁身体还好。分别能买什么？",
        "我爸那个高血压买不了重疾险和医疗险吗？那他能买什么？",
        "惠民保是什么？在哪里买？",
        "你能不能分别给我爸妈做一个方案？我心里有个数。",
    ],
    "s-elderly-003": [
        "我还有两年就退休了，想提前规划一下退休后的保障。",
        "退休后公司的团体险就没了，确实需要自己买一些。",
        "你说意外险和医疗险优先？年金险呢？我听说年金险可以补充养老金。",
        "我不想去体检，有没有免体检的产品？",
        "你说的那个方案我大致了解了，你发个详细的给我看看吧。",
    ],
    # 家庭客户类
    "s-family-001": [
        "你好，我想给一家三口都买上保险。儿子今年3岁，我36，我老婆31。",
        "我们有房贷200万，我年薪大概50万，老婆目前全职在家。",
        "保费预算的话……一年3万左右可以接受吧。",
        "你说先给大人买？但我更关心孩子的保障。",
        "你说的有道理，大人确实是家里的顶梁柱。那你给我做个方案吧。",
    ],
    "s-family-002": [
        "你好，我家宝宝刚满月，我想给他买点保险。",
        "少儿医保已经上了，但我想再买点商业保险。有什么推荐？",
        "教育金有没有必要买？我婆婆说应该存教育金。",
        "5000预算的话，你觉得先买什么比较好？",
        "好的，你说的先买医疗险和意外险，再考虑重疾险，我觉得有道理。具体怎么搭配？",
    ],
    "s-family-003": [
        "说实话，我每个月房贷就要两万，压力很大。保险这事我一直在想，但总下不了手。",
        "我两个孩子还小，万一我出点什么问题，他们怎么办？这个我心里清楚。",
        "定期寿险？具体是什么意思？保一阵子？",
        "一年几百块能保100万？这么便宜？不会有什么猫腻吧。",
        "如果真能这么便宜的话，我倒是可以考虑。你给我算算具体多少。",
    ],
    # 高净值客户类
    "s-hnw-001": [
        "小王啊，坐吧。你说保险？我实话跟你说，我对保险兴趣不大。",
        "我存款少说也有几百万，还有房产和各种投资。我需要保险干什么？",
        "收益率？我做的投资年化至少8%以上，你们保险能有多少？",
        "资产隔离？什么意思？我的资产又不是有问题。",
        "嗯……你说的传承和税务这块我倒是没有仔细想过。你详细说说。",
    ],
    "s-hnw-002": [
        "你好，我时间比较紧张，你大概说几分钟就行。",
        "企业有团险，但那是给员工的。我个人没什么保障配置。",
        "高端医疗？这个我倒是有点兴趣。具体怎么保的？",
        "家企隔离是什么意思？我公司的资产和我个人的有什么关系？",
        "行，你说的有道理。你做个方案发我邮箱吧，我看了再约时间聊。",
    ],
    # 销售技巧类
    "s-skill-001": [
        "前辈，我刚入行三个月，不知道朋友圈该怎么发保险内容。",
        "我发了几次保险的内容，朋友都说我变味了，还有人把我屏蔽了……",
        "那到底应该发什么内容呢？总不能天天发产品介绍吧？",
        "你说先发生活再带保险？能不能给我举个具体的例子？",
        "这样啊，我大概懂了。你能不能帮我规划一下一个月发什么内容？",
    ],
    "s-skill-002": [
        "哎呀，是你啊。上次不是说了不需要吗？",
        "你怎么又来了……我不是没时间吗。",
        "好吧好吧，你说吧，什么事？快点说啊。",
        "嗯……你说的最近的新产品确实没听过。但你先别急着推销。",
        "行，你把资料发我看看吧。我先了解一下，别催我。",
    ],
    "s-skill-003": [
        "小华啊，你上次帮我处理的理赔挺快的，不错。",
        "转介绍？你是说让我帮你介绍客户？这个……我得想想。",
        "主要是万一我推荐的人买了之后不合适，那我不是得罪人嘛。",
        "你说的也有道理……我身边确实有几个朋友最近问过我保险的事。",
        "行吧，我可以帮你问问，但不能保证啊。你别给我太大压力。",
    ],
}

# ==================================================================
# Demo scoring templates
# ==================================================================

_DEMO_SCORE_TEMPLATES = [
    {
        "total_score": 82,
        "product_accuracy": 85,
        "empathy": 80,
        "closing_action": 78,
        "strengths": [
            "产品知识掌握扎实，能准确说明产品特点和差异",
            "沟通态度专业，给客户留下良好的印象",
            "能结合客户实际情况进行方案推荐",
        ],
        "weaknesses": [
            "共情表达可以更自然，避免过于公式化",
            "促单环节稍显犹豫，可以在适当时机更果断地提出下一步",
        ],
        "recommendations": [
            "在客户表达顾虑时，先复述客户的问题再解答，增强被理解的感觉",
            "练习使用假设成交法：\"如果我们能解决您的XX顾虑，您是否愿意……\"",
            "准备2-3个真实的理赔案例，在适当时机自然地分享给客户",
        ],
    },
    {
        "total_score": 68,
        "product_accuracy": 72,
        "empathy": 65,
        "closing_action": 65,
        "strengths": [
            "基本的产品信息传达正确",
            "态度认真，有服务意识",
        ],
        "weaknesses": [
            "对客户情绪的感知不够敏感，急于进入产品介绍",
            "回答过于笼统，缺少具体数据和案例支撑",
            "未能在对话中有效推动下一步行动",
        ],
        "recommendations": [
            "加强倾听训练，让客户说完再回应，不要打断",
            "准备常用的数据卡片（如社保报销比例、重疾发病率等），做到脱口而出",
            "每次沟通结束前，务必给出一个明确的下一步动作",
        ],
    },
    {
        "total_score": 91,
        "product_accuracy": 93,
        "empathy": 90,
        "closing_action": 88,
        "strengths": [
            "产品知识非常扎实，能深入浅出地解释复杂概念",
            "共情能力出色，让客户感受到真诚的关心",
            "节奏把控好，在适当的时机提出促单动作",
            "善于用具体的数字和案例增强说服力",
        ],
        "weaknesses": [
            "可以适当增加一些开放性提问，让客户更多地表达",
        ],
        "recommendations": [
            "尝试使用SPIN提问法，通过系列问题引导客户自我发现需求",
            "在促成阶段可以更自信一些，你已经具备了专业能力",
        ],
    },
]


# ==================================================================
# In-memory demo storage
# ==================================================================

_demo_sessions: dict[str, dict] = {}
_demo_messages: dict[str, list[dict]] = {}
_demo_scores: dict[str, dict] = {}


def _sse_event(event_type: str, data: dict) -> str:
    """构造 SSE 事件 JSON 字符串。"""
    return json.dumps({"event": event_type, "data": data}, ensure_ascii=False)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_random(lst: list) -> str:
    return random.choice(lst)


# ---- 陪练系统提示词（用于AI客户角色扮演） ----

_ROLEPLAY_SYSTEM_PROMPT = """你正在扮演一位保险潜在客户，参加销售模拟训练。你需要完全进入角色，像一个真实的客户一样回应代理人的话术。

## 你的角色设定
{persona_info}

## 演练规则
1. 始终保持角色人设，不要跳出角色
2. 根据代理人的表现自然回应（做得好可以表现出兴趣，做得差要提出质疑）
3. 如果代理人说了不专业的话，表现出怀疑或不信任
4. 逐步展现你的异议和顾虑，不要一次性全部抛出
5. 可以适当"刁难"代理人，提出常见的客户异议
6. 如果代理人表现优秀，可以表现出购买意向
7. 回复控制在50-150字，模拟真实对话节奏

## 当前对话历史
{conversation_history}"""


class TrainingService:
    """AI 陪练服务 —— Demo模式使用内存数据，生产模式使用数据库。"""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        self.db = session
        self.gateway = get_ai_gateway()

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    async def get_scenarios(
        self,
        difficulty: str | None = None,
        product_focus: str | None = None,
    ) -> list[dict]:
        """列出可用场景（支持过滤）。"""
        if settings.DEMO_MODE:
            return await self._demo_get_scenarios(difficulty, product_focus)
        # 生产模式：使用 Repository
        return []

    async def _demo_get_scenarios(self, difficulty=None, product_focus=None) -> list[dict]:
        """Demo: 列出可用场景。"""
        scenarios = _DEMO_SCENARIOS
        if difficulty:
            scenarios = [s for s in scenarios if s["difficulty"] == difficulty]
        if product_focus:
            scenarios = [s for s in scenarios if s.get("product_focus", "") == product_focus]
        return [{
            "id": s["id"], "title": s["title"], "description": s["description"],
            "difficulty": s["difficulty"], "product_focus": s.get("product_focus"),
            "sales_stage": s.get("sales_stage"), "duration_minutes": s["duration_minutes"],
            "customer_persona": s["customer_persona"], "category": s.get("category", ""),
        } for s in scenarios]

    async def get_scenario(self, scenario_id: str) -> dict | None:
        """获取场景详情。"""
        if settings.DEMO_MODE:
            return self._demo_get_scenario(scenario_id)
        return None

    def _demo_get_scenario(self, scenario_id: str) -> dict | None:
        """Demo: 获取场景详情。"""
        for s in _DEMO_SCENARIOS:
            if s["id"] == scenario_id:
                return {
                    "id": s["id"],
                    "title": s["title"],
                    "description": s["description"],
                    "difficulty": s["difficulty"],
                    "product_focus": s.get("product_focus"),
                    "sales_stage": s.get("sales_stage"),
                    "duration_minutes": s["duration_minutes"],
                    "customer_persona": s["customer_persona"],
                    "evaluation_criteria": s.get("evaluation_criteria", {}),
                    "category": s.get("category", ""),
                }
        return None

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def start_session(self, user_id: str, scenario_id: str) -> dict:
        """开始一个新的训练会话。"""
        if settings.DEMO_MODE:
            return await self._demo_start_session(user_id, scenario_id)
        raise ValueError("生产模式暂未实现")

    async def _demo_start_session(self, user_id: str, scenario_id: str) -> dict:
        """Demo: 开始训练会话。"""
        scenario = await self._demo_get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"场景 {scenario_id} 不存在")

        session_id = str(uuid.uuid4())
        now = _iso_now()

        session = {
            "id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "scenario_title": scenario["title"],
            "status": "active",
            "started_at": now,
            "completed_at": None,
            "message_count": 0,
        }
        _demo_sessions[session_id] = session
        _demo_messages[session_id] = []

        return session

    async def list_sessions(self, user_id: str) -> list[dict]:
        """列出用户的训练会话。"""
        if settings.DEMO_MODE:
            return await self._demo_list_sessions(user_id)
        return []

    async def _demo_list_sessions(self, user_id: str) -> list[dict]:
        """Demo: 列出用户训练会话。"""
        user_sessions = [
            s for s in _demo_sessions.values() if s["user_id"] == user_id
        ]
        result = []
        for s in user_sessions:
            score_info = _demo_scores.get(s["id"])
            result.append({
                "id": s["id"],
                "scenario_id": s.get("scenario_id"),
                "scenario_title": s.get("scenario_title"),
                "status": s["status"],
                "started_at": s["started_at"],
                "completed_at": s.get("completed_at"),
                "message_count": s["message_count"],
                "total_score": score_info["total_score"] if score_info else None,
            })
        return sorted(result, key=lambda x: x["started_at"], reverse=True)

    async def get_session(self, session_id: str, user_id: str) -> dict | None:
        """获取会话详情（含消息）。"""
        if settings.DEMO_MODE:
            return self._demo_get_session(session_id, user_id)
        return None

    def _demo_get_session(self, session_id: str, user_id: str) -> dict | None:
        """Demo: 获取会话详情。"""
        session = _demo_sessions.get(session_id)
        if session is None or session["user_id"] != user_id:
            return None

        score_info = _demo_scores.get(session_id)
        messages = _demo_messages.get(session_id, [])

        return {
            "id": session["id"],
            "scenario_id": session.get("scenario_id"),
            "scenario_title": session.get("scenario_title"),
            "status": session["status"],
            "started_at": session["started_at"],
            "completed_at": session.get("completed_at"),
            "message_count": session["message_count"],
            "total_score": score_info["total_score"] if score_info else None,
            "messages": messages,
        }

    # ------------------------------------------------------------------
    # Send message (SSE)
    # ------------------------------------------------------------------

    async def send_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """处理代理人消息，返回 AI 客户响应 + 教练辅导 (SSE)。"""
        if settings.DEMO_MODE:
            async for event in self._demo_send_message(session_id, user_id, content):
                yield event
            return
        yield _sse_event("error", {"message": "生产模式暂未实现"})

    async def _demo_send_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """Demo: 处理代理人消息 (SSE)。"""
        session = _demo_sessions.get(session_id)
        if session is None or session["user_id"] != user_id:
            yield _sse_event("error", {"message": "会话不存在或无权访问"})
            return
        if session["status"] != "active":
            yield _sse_event("error", {"message": "会话已结束"})
            return

        # 保存代理人消息
        agent_msg = {
            "id": str(uuid.uuid4()),
            "role": "agent",
            "content": content,
            "created_at": _iso_now(),
            "score": None,
            "coaching_hint": None,
        }
        _demo_messages[session_id].append(agent_msg)
        session["message_count"] += 1
        turn_index = session["message_count"] // 2  # 每2条=1轮 (agent+customer)

        # 获取场景的预设客户回复（Demo模式优先使用预写回复）
        scenario_id = session.get("scenario_id", "")
        responses = _DEMO_CUSTOMER_RESPONSES.get(scenario_id, [])
        customer_reply = ""
        used_ai = False

        if responses:
            reply_index = min(turn_index, len(responses) - 1)
            customer_reply = responses[reply_index]
        else:
            # 使用AI Gateway动态生成客户回复
            try:
                scenario = await self.get_scenario(scenario_id)
                persona = scenario.get("customer_persona", {}) if scenario else {}

                persona_info = (
                    f"姓名：{persona.get('name', '客户')}\n"
                    f"年龄：{persona.get('age', 40)}岁\n"
                    f"性格：{persona.get('personality', '理性')}\n"
                    f"情绪：{persona.get('mood', '中性')}\n"
                    f"背景：{persona.get('background', '')}\n"
                    f"保险认知：{persona.get('insurance_knowledge', '一般')}\n"
                    f"关键异议：{'、'.join(persona.get('key_objections', []))}"
                )

                # 构建对话历史
                history_msgs = _demo_messages.get(session_id, [])
                history_str = ""
                for msg in history_msgs[-10:]:  # 最近10条
                    role_label = "代理人" if msg["role"] == "agent" else "客户"
                    history_str += f"{role_label}：{msg['content']}\n"

                system_prompt = _ROLEPLAY_SYSTEM_PROMPT.format(
                    persona_info=persona_info,
                    conversation_history=history_str or "（这是对话开始）",
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ]

                # 调用AI Gateway
                full_reply = ""
                stream = await self.gateway.chat(messages=messages, stream=True)
                async for token in stream:
                    full_reply += token
                customer_reply = full_reply[:300]  # 限制回复长度
                used_ai = True
            except Exception as e:
                logger.warning("training_ai_customer_failed", error=str(e))
                customer_reply = "嗯，你说的我考虑一下。"

        # message_start
        yield _sse_event("message_start", {
            "session_id": session_id,
            "role": "customer",
        })

        # 流式输出客户回复
        import asyncio
        chunk_size = random.choice([2, 3, 4])
        i = 0
        while i < len(customer_reply):
            chunk = customer_reply[i:i + chunk_size]
            yield _sse_event("token", {"content": chunk})
            i += chunk_size
            await asyncio.sleep(random.uniform(0.03, 0.07))

        # 保存客户消息
        customer_msg = {
            "id": str(uuid.uuid4()),
            "role": "customer",
            "content": customer_reply,
            "created_at": _iso_now(),
            "score": None,
            "coaching_hint": None,
        }
        _demo_messages[session_id].append(customer_msg)
        session["message_count"] += 1

        # 教练辅导
        coach_category = random.choice(["empathy", "product", "closing"])
        hints = _COACHING_HINTS.get(coach_category, [])
        coach_hint = _pick_random(hints) if hints else "💡 继续保持，注意倾听客户需求。"

        coaching_data = {
            "hint": coach_hint,
            "category": coach_category,
        }
        yield _sse_event("coaching", coaching_data)

        # 保存教练消息
        coach_msg = {
            "id": str(uuid.uuid4()),
            "role": "coach",
            "content": coach_hint,
            "created_at": _iso_now(),
            "score": None,
            "coaching_hint": coaching_data,
        }
        _demo_messages[session_id].append(coach_msg)

        # turn_complete
        yield _sse_event("turn_complete", {
            "message_count": session["message_count"],
        })

    # ------------------------------------------------------------------
    # Complete session (SSE)
    # ------------------------------------------------------------------

    async def complete_session(
        self,
        session_id: str,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """结束训练会话，生成分数 (SSE)。"""
        if settings.DEMO_MODE:
            async for event in self._demo_complete_session(session_id, user_id):
                yield event
            return
        yield _sse_event("error", {"message": "生产模式暂未实现"})

    async def _demo_complete_session(
        self,
        session_id: str,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Demo: 结束训练会话 (SSE)。"""
        session = _demo_sessions.get(session_id)
        if session is None or session["user_id"] != user_id:
            yield _sse_event("error", {"message": "会话不存在或无权访问"})
            return
        if session["status"] != "active":
            yield _sse_event("error", {"message": "会话已结束"})
            return

        # 标记完成
        session["status"] = "completed"
        session["completed_at"] = _iso_now()

        # scoring_start
        yield _sse_event("scoring_start", {"session_id": session_id})

        import asyncio

        # 模拟评分过程
        analysis_texts = [
            "正在分析您的对话表现...",
            "评估产品知识准确性...",
            "分析客户共情表现...",
            "评价促单技巧...",
            "生成综合评分报告...",
        ]
        for text in analysis_texts:
            for i in range(0, len(text), 3):
                chunk = text[i:i+3]
                yield _sse_event("token", {"content": chunk})
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.15)

        # 生成评分（根据消息数量调整）
        msg_count = session["message_count"]
        template = random.choice(_DEMO_SCORE_TEMPLATES)

        # 消息越多分越高（有上限）
        bonus = min(msg_count // 4, 10)
        total = min(template["total_score"] + bonus, 98)
        pa = min(template["product_accuracy"] + random.randint(-3, 5), 98)
        em = min(template["empathy"] + random.randint(-3, 5), 98)
        ca = min(template["closing_action"] + random.randint(-3, 5), 98)

        score_data = {
            "total_score": total,
            "product_accuracy": pa,
            "empathy": em,
            "closing_action": ca,
            "strengths": template["strengths"],
            "weaknesses": template["weaknesses"],
            "recommendations": template["recommendations"],
        }

        # 保存评分
        _demo_scores[session_id] = score_data

        yield _sse_event("score_data", score_data)
        yield _sse_event("scoring_complete", {"session_id": session_id})

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self, user_id: str) -> dict:
        """获取训练统计。"""
        if settings.DEMO_MODE:
            return await self._demo_get_stats(user_id)
        return {"total_sessions": 0, "completed_sessions": 0}

    async def _demo_get_stats(self, user_id: str) -> dict:
        """Demo: 获取训练统计。"""
        user_sessions = [s for s in _demo_sessions.values() if s["user_id"] == user_id]
        total = len(user_sessions)
        completed = [s for s in user_sessions if s["status"] == "completed"]
        completed_count = len(completed)

        scores = [_demo_scores[s["id"]]["total_score"] for s in completed if s["id"] in _demo_scores]
        pa_scores = [_demo_scores[s["id"]]["product_accuracy"] for s in completed if s["id"] in _demo_scores]
        em_scores = [_demo_scores[s["id"]]["empathy"] for s in completed if s["id"] in _demo_scores]
        ca_scores = [_demo_scores[s["id"]]["closing_action"] for s in completed if s["id"] in _demo_scores]

        # 难度分布
        diff_dist: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        for s in user_sessions:
            sid = s.get("scenario_id", "")
            for sc in _DEMO_SCENARIOS:
                if sc["id"] == sid:
                    diff_dist[sc["difficulty"]] = diff_dist.get(sc["difficulty"], 0) + 1
                    break

        # 产品分布
        pf_dist: dict[str, int] = {}
        for s in user_sessions:
            sid = s.get("scenario_id", "")
            for sc in _DEMO_SCENARIOS:
                if sc["id"] == sid:
                    pf = sc.get("product_focus", "其他")
                    pf_dist[pf] = pf_dist.get(pf, 0) + 1
                    break

        # 趋势（模拟最近7天）
        trend = []
        for i in range(6, -1, -1):
            day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            day_sessions = [
                s for s in completed
                if s.get("started_at", "")[:10] == day and s["id"] in _demo_scores
            ]
            if day_sessions:
                day_avg = sum(_demo_scores[s["id"]]["total_score"] for s in day_sessions) / len(day_sessions)
            else:
                day_avg = 0.0
            trend.append({
                "date": day,
                "avg_score": round(day_avg, 1),
                "session_count": len(day_sessions),
            })

        return {
            "total_sessions": total,
            "completed_sessions": completed_count,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
            "avg_product_accuracy": round(sum(pa_scores) / len(pa_scores), 1) if pa_scores else None,
            "avg_empathy": round(sum(em_scores) / len(em_scores), 1) if em_scores else None,
            "avg_closing_action": round(sum(ca_scores) / len(ca_scores), 1) if ca_scores else None,
            "best_score": max(scores) if scores else None,
            "trend": trend,
            "difficulty_distribution": diff_dist,
            "product_focus_distribution": pf_dist,
        }
