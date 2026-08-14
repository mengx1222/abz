"""测试合规检查引擎。"""
from app.services.compliance_service import check_compliance, COMPLIANCE_RULES


class TestCheckCompliance:
    def test_clean_text(self):
        """合规文本应返回 GREEN 状态和满分。"""
        result = check_compliance("这款百万医疗险的保障范围比较广，建议您仔细查看合同条款。")
        assert result["status"] == "GREEN"
        assert result["score"] == 100
        assert result["issues"] == []

    def test_profit_promise(self):
        """收益承诺应触发 RED。"""
        result = check_compliance("买这个保险保证有收益，稳赚不赔")
        assert result["status"] == "RED"
        assert result["score"] < 100
        assert len(result["issues"]) >= 1
        rule_names = [i["rule"] for i in result["issues"]]
        assert "收益承诺" in rule_names

    def test_absolute_expression(self):
        """绝对化表达应触发 YELLOW。"""
        result = check_compliance("这是我们最好的产品")
        assert result["status"] == "YELLOW"
        assert result["score"] < 100
        assert result["score"] >= 80

    def test_fake_comparison(self):
        """虚假比较应触发 YELLOW。"""
        result = check_compliance("我们的产品比其他公司好多了，碾压竞品")
        assert result["status"] == "YELLOW"
        assert len(result["issues"]) >= 1

    def test_exaggerated_coverage(self):
        """夸大保障应触发 RED。"""
        result = check_compliance("买了这个保险什么都能报，全部报销")
        assert result["status"] == "RED"
        assert result["score"] < 100

    def test_underwriting_conclusion(self):
        """不当核保结论应触发 RED。"""
        result = check_compliance("您的身体肯定能过核保")
        assert result["status"] == "RED"
        assert len(result["issues"]) >= 1

    def test_claim_promise(self):
        """不当理赔承诺应触发 RED。"""
        result = check_compliance("买了就一定赔，秒赔")
        assert result["status"] == "RED"

    def test_pressure_sales(self):
        """诱导销售应触发 YELLOW。"""
        result = check_compliance("不买就没有机会了，最后机会")
        assert result["status"] == "YELLOW"

    def test_medical_conclusion(self):
        """敏感医疗结论应触发 RED。"""
        result = check_compliance("这个小问题不算什么，不用告诉公司")
        assert result["status"] == "RED"

    def test_multiple_violations(self):
        """多条违规应累计扣分。"""
        result = check_compliance("保证收益，绝对安全，这是最好的产品")
        assert result["score"] < 80
        assert len(result["issues"]) >= 2

    def test_real_sales_script_compliant(self):
        """合规话术应通过检查。"""
        script = (
            "张先生您好，了解到您对健康保障比较关注，"
            "百万医疗险可以在住院时提供医疗费用报销，"
            "具体赔付以合同条款为准，建议您仔细阅读。"
        )
        result = check_compliance(script)
        assert result["status"] == "GREEN"
        assert result["score"] == 100

    def test_rules_count(self):
        """合规规则库应有 8 条规则。"""
        assert len(COMPLIANCE_RULES) == 8
