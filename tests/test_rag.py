"""
RAG 模块测试
"""

import pytest

from app.rag.indexer import ChromaIndexer
from app.rag.loader import KnowledgeLoader
from app.rag.embeddings import QwenEmbedding


class TestKnowledgeLoader:
    """知识加载器测试"""

    @pytest.fixture
    def loader(self):
        return KnowledgeLoader(chunk_size=500, chunk_overlap=50)

    def test_split_content(self, loader):
        """测试内容分割"""
        content = "这是一个测试段落。\n\n这是另一个测试段落，稍微长一点，看看会不会被正确分割。"
        chunks = loader._split_content(content)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_split_long_paragraph(self, loader):
        """测试长段落分割"""
        long_text = "这是第一句话。" * 100
        chunks = loader._split_long_paragraph(long_text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= loader.chunk_size + 50  # 允许一定容差

    def test_load_markdown_not_found(self, loader):
        """测试加载不存在的文件"""
        result = loader.load_markdown("nonexistent.md")
        assert result == []

    def test_load_directory_not_found(self, loader):
        """测试加载不存在的目录"""
        result = loader.load_directory("nonexistent_dir")
        assert result == []


class TestChromaIndexer:
    """Chroma 索引器测试"""

    @pytest.fixture
    def indexer(self):
        # 使用临时目录
        import tempfile
        temp_dir = tempfile.mkdtemp()
        indexer = ChromaIndexer(
            persist_dir=temp_dir,
            collection_name="test_collection",
        )
        yield indexer
        # 清理
        indexer.clear()

    def test_add_and_search(self, indexer):
        """测试添加和检索"""
        # 添加文档
        documents = [
            {"page_content": "深蹲是练腿的王牌动作", "metadata": {"source": "test1"}},
            {"page_content": "卧推主要锻炼胸肌和三头肌", "metadata": {"source": "test2"}},
        ]

        added = indexer.add_documents(documents)
        assert added == 2

        # 检索
        results = indexer.search("怎么练腿")
        assert len(results) > 0
        assert "深蹲" in results[0]["content"]

    def test_count(self, indexer):
        """测试计数"""
        assert indexer.count() == 0

        indexer.add_documents([
            {"page_content": "测试文档", "metadata": {"source": "test"}},
        ])
        assert indexer.count() == 1

    def test_clear(self, indexer):
        """测试清空"""
        indexer.add_documents([
            {"page_content": "测试", "metadata": {"source": "test"}},
        ])
        assert indexer.count() == 1

        indexer.clear()
        # 重新获取集合
        indexer._collection = None
        assert indexer.count() == 0

    def test_get_stats(self, indexer):
        """测试统计信息"""
        stats = indexer.get_stats()

        assert "collection_name" in stats
        assert "count" in stats
        assert "persist_dir" in stats


class TestQwenEmbedding:
    """Qwen Embedding 测试"""

    @pytest.fixture
    def embedding(self):
        # 跳过如果没有 API Key
        from app.config import settings
        if not settings.dashscope_api_key:
            pytest.skip("未配置 API Key")

        return QwenEmbedding()

    @pytest.mark.skip(reason="需要 API Key")
    def test_embed_query(self, embedding):
        """测试单文本嵌入"""
        vector = embedding.embed_query("测试文本")

        assert isinstance(vector, list)
        assert len(vector) == 1024  # text-embedding-v3 输出 1024 维

    @pytest.mark.skip(reason="需要 API Key")
    def test_embed_documents(self, embedding):
        """测试批量嵌入"""
        texts = ["第一段文本", "第二段文本"]
        vectors = embedding.embed_documents(texts)

        assert len(vectors) == 2
        assert all(len(v) == 1024 for v in vectors)


class TestRAGIntegration:
    """RAG 集成测试"""

    @pytest.fixture
    def setup_indexer(self):
        """设置测试索引器"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        indexer = ChromaIndexer(
            persist_dir=temp_dir,
            collection_name="integration_test",
        )

        # 添加测试文档
        documents = [
            {"page_content": "深蹲主要锻炼股四头肌、臀大肌和腘绳肌", "metadata": {"category": "力量训练"}},
            {"page_content": "卧推是锻炼胸大肌的经典动作", "metadata": {"category": "力量训练"}},
            {"page_content": "减脂需要创造热量缺口", "metadata": {"category": "训练知识"}},
        ]
        indexer.add_documents(documents)

        yield indexer

        indexer.clear()

    def test_search_relevance(self, setup_indexer):
        """测试检索相关性"""
        indexer = setup_indexer

        # 搜索深蹲相关
        results = indexer.search("深蹲锻炼什么肌肉")
        assert len(results) > 0
        assert "深蹲" in results[0]["content"]

    def test_search_multiple_results(self, setup_indexer):
        """测试多个结果返回"""
        indexer = setup_indexer

        results = indexer.search("力量训练", n_results=3)
        assert len(results) <= 3
