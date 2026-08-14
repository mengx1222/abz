"""测试敏感数据脱敏功能。"""
from app.core.sanitize import mask_phone, mask_id_card, mask_bank_card, mask_name, mask_email, sanitize_response_data


class TestMaskPhone:
    def test_normal_phone(self):
        result = mask_phone("13800138000")
        assert result == "138****8000"
        assert "****" in result
        assert len(result) == 11  # 3+4+4

    def test_short_phone(self):
        result = mask_phone("138")
        assert result == "138"
        assert "*" not in result

    def test_empty(self):
        assert mask_phone("") == ""
        assert mask_phone(None) == ""

    def test_already_masked(self):
        result = mask_phone("138****8000")
        assert result == "138****8000"

    def test_with_spaces(self):
        result = mask_phone("  13800138000  ")
        assert result == "138****8000"


class TestMaskIdCard:
    def test_18_digit(self):
        result = mask_id_card("310101199001011234")
        assert result.startswith("310")
        assert result.endswith("1234")
        assert len(result) == 18
        assert result[3:14] == "*" * 11

    def test_15_digit(self):
        result = mask_id_card("310101900101123")
        assert result.startswith("310")
        assert result.endswith("123")
        assert len(result) == 15
        assert result[3:11] == "*" * 8

    def test_empty(self):
        assert mask_id_card("") == ""
        assert mask_id_card(None) == ""

    def test_short(self):
        assert mask_id_card("1234567") == "1234567"


class TestMaskName:
    def test_two_chars(self):
        result = mask_name("张三")
        assert result == "张*"
        assert len(result) == 2

    def test_three_chars(self):
        result = mask_name("张三丰")
        assert result == "张*丰"
        assert len(result) == 3

    def test_four_chars(self):
        result = mask_name("欧阳锋")
        assert result == "欧*锋"
        assert len(result) == 3

    def test_single_char(self):
        assert mask_name("张") == "张"

    def test_empty(self):
        assert mask_name("") == ""
        assert mask_name(None) == ""


class TestMaskEmail:
    def test_normal(self):
        result = mask_email("zhangsan@example.com")
        assert result == "z***@example.com"
        assert result.startswith("z")
        assert "@" in result

    def test_short_local(self):
        result = mask_email("a@example.com")
        assert result == "a***@example.com"

    def test_no_at(self):
        assert mask_email("invalid") == "invalid"

    def test_empty(self):
        assert mask_email("") == ""


class TestMaskBankCard:
    def test_16_digit(self):
        result = mask_bank_card("6222021234567890")
        assert result.startswith("6222")
        assert result.endswith("7890")
        assert "**** ****" in result

    def test_19_digit(self):
        result = mask_bank_card("6222021234567890123")
        assert result.startswith("6222")
        assert result.endswith("0123")

    def test_with_spaces(self):
        result = mask_bank_card("6222 0123 4567 8901")
        assert result.startswith("6222")
        assert result.endswith("8901")

    def test_short(self):
        assert mask_bank_card("1234567") == "1234567"


class TestSanitizeResponseData:
    def test_flat_dict(self):
        data = {"name": "张三", "phone": "13800138000", "age": 30}
        rules = {"phone": "phone"}
        result = sanitize_response_data(data, rules)
        assert result["phone"] == "138****8000"
        assert result["name"] == "张三"
        assert result["age"] == 30

    def test_nested_dict(self):
        data = {"user": {"name": "张三", "phone": "13800138000"}}
        rules = {"phone": "phone"}
        result = sanitize_response_data(data, rules)
        assert result["user"]["phone"] == "138****8000"

    def test_list_of_dicts(self):
        data = [
            {"name": "张三", "phone": "13800138000"},
            {"name": "李四", "phone": "13900139000"},
        ]
        rules = {"phone": "phone"}
        result = sanitize_response_data(data, rules)
        assert result[0]["phone"] == "138****8000"
        assert result[1]["phone"] == "139****9000"

    def test_no_matching_rules(self):
        data = {"name": "张三", "age": 30}
        rules = {"phone": "phone"}
        result = sanitize_response_data(data, rules)
        assert result == {"name": "张三", "age": 30}

    def test_multiple_rules(self):
        data = {"phone": "13800138000", "id_card": "310101199001011234"}
        rules = {"phone": "phone", "id_card": "id_card"}
        result = sanitize_response_data(data, rules)
        assert result["phone"] == "138****8000"
        assert "*" in result["id_card"]
