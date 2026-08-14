"""敏感数据脱敏工具 —— 手机号、身份证、银行卡等。"""


def mask_phone(phone: str) -> str:
    """手机号脱敏: 138****8000"""
    phone = (phone or "").strip()
    if len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]


def mask_id_card(id_card: str) -> str:
    """身份证脱敏: 310***********1234"""
    id_card = (id_card or "").strip()
    if len(id_card) < 8:
        return id_card
    return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]


def mask_bank_card(card: str) -> str:
    """银行卡脱敏: 6222 **** **** 1234"""
    card = (card or "").replace(" ", "").strip()
    if len(card) < 8:
        return card
    return card[:4] + " **** **** " + card[-4:]


def mask_name(name: str) -> str:
    """姓名脱敏: 张* / 张*丰"""
    name = (name or "").strip()
    if not name:
        return name
    length = len(name)
    if length <= 1:
        return name
    if length == 2:
        return name[0] + "*"
    # 三个字及以上：首字 + * + 末字
    return name[0] + "*" * (length - 2) + name[-1]


def mask_email(email: str) -> str:
    """邮箱脱敏: z***@example.com"""
    email = (email or "").strip()
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***@{domain}"


# 脱敏函数映射
_MASK_FUNCTIONS: dict[str, type(lambda: str)] = {
    "phone": mask_phone,
    "id_card": mask_id_card,
    "bank_card": mask_bank_card,
    "name": mask_name,
    "email": mask_email,
}


def sanitize_response_data(data: dict | list, rules: dict) -> dict | list:
    """递归遍历响应数据，根据 rules 对指定字段脱敏。

    Args:
        data: 响应数据（dict 或 list）
        rules: 字段名 -> 脱敏类型 的映射，如
               {"phone": "phone", "id_card": "id_card", "customer_name": "name"}

    Returns:
        脱敏后的数据
    """
    if isinstance(data, dict):
        return {
            k: _MASK_FUNCTIONS[rules[k]](v) if k in rules and isinstance(v, str) and _MASK_FUNCTIONS.get(rules[k]) else sanitize_response_data(v, rules)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_response_data(item, rules) for item in data]
    return data
