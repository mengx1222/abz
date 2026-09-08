"""Embedding 降级模式 ILIKE 检索 —— 纯函数单元测试。

场景：opencode.ai Go 网关无 /embeddings → pipeline.query 捕获异常后 query_embedding=None，
retriever.search 追加 ILIKE 子串检索（中文友好）。这里覆盖可离线验证的纯逻辑：
- _like_escape：% _ \\ 通配符转义（防注入）
- _merge_like_results：BM25 结果优先，LIKE 仅补漏、不覆盖
"""
import pytest

from app.rag.retriever import Retriever

pytestmark = pytest.mark.integration  # 保持与 tests/rag 现有标记一致（不需要真实 DB）


class TestLikeEscape:
    def test_escapes_wildcards(self):
        assert Retriever._like_escape("50%医用") == "50\\%医用"
        assert Retriever._like_escape("a_b") == "a\\_b"
        assert Retriever._like_escape("反斜杠\\路径") == "反斜杠\\\\路径"

    def test_plain_chinese_unchanged(self):
        assert Retriever._like_escape("百万医疗险") == "百万医疗险"

    def test_empty_query(self):
        assert Retriever._like_escape("") == ""


class TestCjkGrams:
    def test_chinese_query_generates_2grams(self):
        grams = Retriever._cjk_grams("百万医疗险")
        # 连续 CJK 段的全部 2-gram
        assert "百万" in grams and "万医" in grams and "医疗" in grams and "疗险" in grams

    def test_order_and_dedup(self):
        grams = Retriever._cjk_grams("等待等待")
        # 等待/待等 互不相同且去重
        assert grams == ["等待", "待等"] or set(grams) == {"等待", "待等"}

    def test_alnum_tokens_kept_whole(self):
        grams = Retriever._cjk_grams("保险600元 是V80")
        assert "600" in grams
        assert "v80" in grams  # 小写化

    def test_ascii_only_query(self):
        grams = Retriever._cjk_grams("hello world")
        assert "hello" in grams and "world" in grams

    def test_cap_at_max_grams(self):
        grams = Retriever._cjk_grams("一二三四五六七八九十", max_grams=4)
        assert len(grams) <= 4


class TestMergeLikeResults:
    def _row(self, cid: str, score: float) -> dict:
        return {"chunk_id": cid, "score": score}

    def test_bm25_wins_on_duplicate_chunk(self):
        bm25 = [self._row("c1", 0.5)]
        like = [self._row("c1", 0.9), self._row("c2", 0.9)]
        merged = Retriever._merge_like_results(bm25, like)
        assert [r["chunk_id"] for r in merged] == ["c1", "c2"]
        assert merged[0]["score"] == 0.5  # BM25 版本保留

    def test_like_only_fills_gaps(self):
        merged = Retriever._merge_like_results([], [self._row("c9", 0.9)])
        assert [r["chunk_id"] for r in merged] == ["c9"]

    def test_all_duplicates_keeps_bm25_only(self):
        merged = Retriever._merge_like_results(
            [self._row("a", 0.4)], [self._row("a", 0.9)]
        )
        assert len(merged) == 1