"""测试 JWT 认证。"""
import time

import pytest
from jose import JWTError

from app.core.security import create_access_token, create_refresh_token, decode_token


class TestCreateToken:
    def test_access_token(self):
        token = create_access_token({"sub": "user123", "phone": "13800138000"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token(self):
        token = create_refresh_token({"sub": "user123", "phone": "13800138000"})
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_custom_expiry(self):
        """不同类型 token 有不同过期时间。"""
        access = create_access_token({"sub": "user123"})
        refresh = create_refresh_token({"sub": "user123"})
        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)
        # Refresh token 过期时间应远大于 access token
        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    def test_valid_token(self):
        data = {"sub": "user123", "phone": "13800138000"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["phone"] == "13800138000"
        assert payload["type"] == "access"

    def test_expired_token(self):
        from datetime import timedelta, timezone, datetime
        from jose import jwt
        from app.core.config import settings
        expired_payload = {
            "sub": "user123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(JWTError):
            decode_token(token)

    def test_wrong_secret(self):
        from jose import jwt
        payload = {"sub": "user123", "type": "access"}
        token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_token(token)

    def test_missing_claim(self):
        """token 缺少 type claim，解码成功但 type 字段不存在。"""
        from jose import jwt
        from app.core.config import settings
        payload = {"sub": "user123"}  # 缺少 type
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = decode_token(token)
        assert result.get("type") is None
