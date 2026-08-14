展示模式预置话术数据（30条）。

按 客户 x 产品 x 风格 组织，覆盖不同异议场景和合规状态。
"""
import uuid
from datetime import datetime, timezone


def build_demo_scripts() -> list[dict]:
    """构建30条演示话术。"""
    now = datetime.now(timezone.utc)
    ts = now.isoformat()

    return [
        # === 1-4: 陈志明 45岁 价格异议 医疗险 ===
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-1")),
            "title": "百万医疗险 — 陈志明价格异议（亲和型）",
            "customer_context": {"name": "陈志明", "age": 45, "type": "个人", "stage": "方案推荐", "objection": "觉得保费太贵"},
            "style": "affinity",
            "content": (
                "陈先生，我特别理解您的顾虑。谁不希望每一分钱都花在刀刃上呢？\n\n"
                "我跟您分享一个真实的故事。去年一位跟您年纪相仿的客户，也觉得医疗险不便宜。"
                "结果半年后因急性阑尾炎住院，手术加住院费花了 two万多。幸好他买了百万医疗险，"
                "扣除一万免赔额后，剩下的一万多全报销了。\n\n"
                "陈先生，咱们出去吃顿饭就几百块，但这几百块买的是一整年的安心。"
                "华安百万医疗险45岁男性保费一年1000出头，平均每天不到3块钱。"
                "这不是花费，这是给家人的一份保障。"
            ),
            "product_type": "医疗险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 12, "usage_count": 45,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-2")),
            "title": "百万医疗险 — 陈志明价格异议（专业型）",
            "customer_context": {"name": "陈志明", "age": 45, "type": "个人", "stage": "方案推荐", "objection": "觉得保费太贵"},
            "style": "professional",
            "content": (
                "陈先生，我从专业角度为您做一个成本效益分析。\n\n"
                "华安百万医疗险45岁男性年保费约1200元，保障额度最高600万元。"
                "根据国家卫健委数据，45-55岁是疾病高发期，该年龄段住院概率约为8.5%，平均住院费用约2.5万元。\n\n"
                "对比来看：\n1. 不投保：风险自担，一旦发生重大疾病，费用可能达到数十万\n"
                "2. 投保百万医疗险：年成本1200元，获得最高600万保额的医疗保障\n\n"
                "该产品包含质子重离子治疗保障和外购药报销，保证续保。"
                "1200元/年的成本撬动600万的保障杠杆，杠杆率达到5000倍。"
            ),
            "product_type": "医疗险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 8, "usage_count": 32,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-3")),
            "title": "百万医疗险 — 陈志明价格异议（数据驱动型）",
            "customer_context": {"name": "陈志明", "age": 45, "type": "个人", "stage": "方案推荐", "objection": "觉得保费太贵"},
            "style": "data_driven",
            "content": (
                "陈先生，我用几组数据帮您算一笔账：\n\n"
                "【保费投入】年保费1200元 x 20年 = 2.4万元总投入\n\n"
                "【风险数据】国家卫健委2023年统计：\n"
                "- 45-55岁男性重大疾病发病率：约12‰/年\n"
                "- 平均住院费用：2.5-8万元\n"
                "- 重大疾病平均治疗费用：15-50万元\n\n"
                "【保障对比】普通住院2.5万：自费2.5万 vs 有险自付1万报销1.5万；"
                "重大疾病30万：自费30万 vs 有险自付1万报销29万\n\n"
                "【ROI分析】假设20年内发生一次重大疾病：投入2.4万，报销29万+，净收益26.6万+。"
                "45岁男性20年内重疾累计发生率约24%，期望赔付额约7.2万。"
            ),
            "product_type": "医疗险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 15, "usage_count": 58,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-4")),
            "title": "百万医疗险 — 陈志明价格异议（简洁型）",
            "customer_context": {"name": "陈志明", "age": 45, "type": "个人", "stage": "方案推荐", "objection": "觉得保费太贵"},
            "style": "concise",
            "content": (
                "陈先生，三句话跟您说清楚：\n\n"
                "第一，一天不到3块钱，买600万医疗保障。\n\n"
                "第二，45岁以后是疾病高发期，一场大病平均花费30万，不买险就是自掏腰包。\n\n"
                "第三，华安百万医疗险保证续保，买了就不怕以后买不到。\n\n"
                "省下一顿饭钱，换一整年的安心。您觉得值不值？"
            ),
            "product_type": "医疗险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 20, "usage_count": 72,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },

        # === 5-8: 王丽华 38岁 健康顾虑 重疾险 ===
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-5")),
            "title": "重疾险 — 王丽华健康顾虑（亲和型）",
            "customer_context": {"name": "王丽华", "age": 38, "type": "个人", "stage": "需求挖掘", "objection": "担心自己健康状况"},
            "style": "affinity",
            "content": (
                "王姐，听到您这么说，我真的很心疼。作为两个孩子的妈妈，您总是把家人放在第一位，却很少关心自己。\n\n"
                "其实很多妈妈都是这样。但您有没有想过，您才是这个家最重要的顶梁柱？如果妈妈倒了，谁来照顾孩子？\n\n"
                "我之前服务过一位跟您情况很像的客户，也是38岁的妈妈。后来她给自己配置了一份重疾险。她跟我说：'不是我不相信自己的身体，而是我要对得起孩子。'\n\n"
                "王姐，重疾险不是不信任自己的健康，而是一种负责任的态度。华安重疾险覆盖120多种重大疾病，确诊就赔。咱们先了解一下，好吗？"
            ),
            "product_type": "重疾险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 18, "usage_count": 63,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-6")),
            "title": "重疾险 — 王丽华健康顾虑（专业型）",
            "customer_context": {"name": "王丽华", "age": 38, "type": "个人", "stage": "需求挖掘", "objection": "担心自己健康状况"},
            "style": "professional",
            "content": (
                "王女士，您关注自身健康状况，说明有很好的风险意识。我为您详细说明重疾险的保障逻辑。\n\n"
                "华安重疾险核心保障分三个层次：\n"
                "1. 重度疾病保障：覆盖120+种重大疾病，赔付100%基本保额，占所有重疾理赔的95%以上\n"
                "2. 中度疾病保障：覆盖25种中度疾病，赔付60%基本保额，最多赔付3次\n"
                "3. 轻度疾病保障：覆盖50种轻度疾病，赔付30%基本保额，最多赔付3次\n\n"
                "产品包含被保人豁免条款，确诊轻中症后后续保费全部豁免。\n"
                "关于健康告知：投保时需如实填写健康问卷，有既往症可提交资料核保，具体以核保结果为准。"
            ),
            "product_type": "重疾险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 10, "usage_count": 28,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-7")),
            "title": "重疾险 — 王丽华健康顾虑（数据驱动型）",
            "customer_context": {"name": "王丽华", "age": 38, "type": "个人", "stage": "需求挖掘", "objection": "担心自己健康状况"},
            "style": "data_driven",
            "content": (
                "王女士，用数据理性分析您当前的风险敞口：\n\n"
                "【女性健康风险数据】来源：国家癌症中心2023年报\n"
                "- 35-39岁女性癌症发病率：约180/10万\n"
                "- 女性高发重疾Top3：乳腺癌、甲状腺癌、宫颈癌\n"
                "- 乳腺癌平均治疗费用：12-25万元\n\n"
                "【保障方案测算】假设年家庭收入30万，建议重疾保额=30万x3=90万（取整100万）\n"
                "38岁女性100万保额重疾险：年保费约8000-12000元\n\n"
                "【成本效益分析】100万保额覆盖：治疗费12-25万+3年收入损失90万=合计102-115万。"
                "保费20年总投入16-24万，杠杆比4.2-6.3倍。从财务角度看是合理的风险对冲。"
            ),
            "product_type": "重疾险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 14, "usage_count": 41,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-8")),
            "title": "重疾险 — 王丽华健康顾虑（简洁型）",
            "customer_context": {"name": "王丽华", "age": 38, "type": "个人", "stage": "需求挖掘", "objection": "担心自己健康状况"},
            "style": "concise",
            "content": (
                "王姐，跟您说三个事实：\n\n"
                "第一，35-40岁是女性重疾高发期，乳腺癌发病率逐年上升。\n\n"
                "第二，一场重疾平均花费30万，加上3年不能工作，损失近百万。\n\n"
                "第三，华安重疾险100万保额，年保费不到1万，确诊即赔。\n\n"
                "您照顾好了自己，才是对孩子最大的负责。"
            ),
            "product_type": "重疾险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 22, "usage_count": 85,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },

        # === 9-12: 张伟 30岁 不需要保险 意外险 ===
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-9")),
            "title": "意外险 — 张伟不需要保险（亲和型）",
            "customer_context": {"name": "张伟", "age": 30, "type": "个人", "stage": "初次接触", "objection": "觉得自己年轻不需要保险"},
            "style": "affinity",
            "content": (
                "张哥，我太理解您了！我30岁的时候也是这么想的——年轻力壮，保险是给中年人准备的。\n\n"
                "但您知道吗，我后来改变想法不是因为看了什么统计数据，而是因为身边发生的事。"
                "我大学同学，比咱们还年轻，去年骑电动车被闯红灯的车撞了，腿骨折住了两个月的院。"
                "他没买意外险，住院费加误工费，自己掏了近5万。\n\n"
                "张哥，意外从来不挑年龄。华安综合意外险一年才100多块钱，100万保额。"
                "您就当每年花100块买个平安符，这不比什么都重要吗？"
            ),
            "product_type": "意外险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 9, "usage_count": 36,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-10")),
            "title": "意外险 — 张伟不需要保险（专业型）",
            "customer_context": {"name": "张伟", "age": 30, "type": "个人", "stage": "初次接触", "objection": "觉得自己年轻不需要保险"},
            "style": "professional",
            "content": (
                "张先生，关于'年轻人不需要保险'这个观点，我从专业的风险管理角度来分析。\n\n"
                "首先，意外险是所有保险中价格最低、杠杆最高的险种。华安综合意外险30岁男性年保费仅需150元左右，"
                "提供意外身故/伤残100万、意外医疗5万、住院津贴100元/天的保障。\n\n"
                "其次，意外风险与年龄并非负相关。根据中国疾控中心数据，18-40岁人群意外伤害发生率在各年龄段中位居前列，"
                "交通事故、运动损伤、工作伤害是主要原因。\n\n"
                "第三，意外险没有健康告知要求，投保门槛最低。建议作为保险配置的第一步，配合医疗险形成基础保障。"
            ),
            "product_type": "意外险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", "favorited_count": 7, "usage_count": 22,
            "is_favorited": False, "created_at": ts, "updated_at": ts,
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-script-11")),
            "title": "意外险 — 张伟不需要保险（数据驱动型）",
            "customer_context": {"name": "张伟", "age": 30, "type": "个人", "stage": "初次接触", "objection": "觉得自己年轻不需要保险"},
            "style": "data_driven",
            "content": (
                "张先生，用数据说话：\n\n"
                "【意外风险数据】来源：中国疾控中心2023年报告\n"
                "- 中国每年因意外死亡约70万人\n"
                "- 18-44岁人群意外伤害发生率：约15%\n"
                "- 交通事故年均死亡约6万人，受伤约25万人\n"
                "- 30岁男性意外住院平均费用：2-8万元\n\n"
                "【投入产出分析】\n"
                "华安综合意外险30岁男性：年保费150元\n"
                "保障：意外身故/伤残100万+意外医疗5万+住院津贴100元/天\n"
                "杠杆比：6667倍\n\n"
                "【风险敞口】30岁男性年收入假设15万，意外导致6个月不能工作=损失7.5万+医疗费3万=10.5万。150元保费可覆盖绝大部分。"
            ),
            "product_type": "意外险", "compliance_status": "green", "compliance_issues": [],
            "version": 1, "status": "published", 