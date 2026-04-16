"""
Chroma 向量索引器
"""

import os
import time
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import settings
from app.rag.embeddings import QwenEmbedding, get_embedding_model
from app.utils import get_logger
from app.utils.metrics import record_rag_hit

logger = get_logger(__name__)


class ChromaIndexer:
    """
    Chroma 向量索引器

    Features:
    - 文档嵌入和索引
    - 语义检索
    - 集合管理
    - 持久化存储
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ):
        """
        初始化索引器

        Args:
            persist_dir: 持久化目录
            collection_name: 集合名称
        """
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name

        # 确保目录存在
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # 初始化 Chroma 客户端
        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None
        self._embedding_model: QwenEmbedding | None = None

    @property
    def client(self) -> chromadb.Client:
        """获取 Chroma 客户端"""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    @property
    def embedding_model(self) -> QwenEmbedding:
        """获取嵌入模型"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def get_collection(self) -> chromadb.Collection:
        """
        获取或创建集合

        Returns:
            Chroma 集合
        """
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "集合已加载",
                collection_name=self.collection_name,
                count=self._collection.count(),
            )
        return self._collection

    def add_documents(
        self,
        documents: list[dict[str, Any]],
        ids: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> int:
        """
        添加文档到索引

        Args:
            documents: 文档列表，每个文档包含 page_content 和 metadata
            ids: 文档 ID 列表
            metadatas: 元数据列表

        Returns:
            添加的文档数量
        """
        if not documents:
            return 0

        collection = self.get_collection()

        # 提取文本内容
        texts = []
        doc_metadatas = []
        doc_ids = []

        for i, doc in enumerate(documents):
            if isinstance(doc, dict):
                text = doc.get("page_content", "") or doc.get("content", "")
                metadata = doc.get("metadata", {})
            else:
                text = str(doc)
                metadata = {}

            if text:
                texts.append(text)
                doc_metadatas.append(metadatas[i] if metadatas else metadata)
                doc_ids.append(ids[i] if ids else f"doc_{i}_{hash(text)}")

        if not texts:
            return 0

        # 生成嵌入向量
        start = time.perf_counter()
        embeddings = self.embedding_model.embed_documents(texts)
        embed_time = (time.perf_counter() - start) * 1000

        # 添加到集合
        collection.add(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=doc_metadatas,
        )

        logger.info(
            "文档已索引",
            count=len(texts),
            embed_time_ms=round(embed_time, 2),
            total_count=collection.count(),
        )

        return len(texts)

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        语义检索

        Args:
            query: 查询文本
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            检索结果列表
        """
        collection = self.get_collection()

        # 生成查询向量
        start = time.perf_counter()
        query_embedding = self.embedding_model.embed_query(query)
        embed_time = (time.perf_counter() - start) * 1000

        # 检索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
        )

        search_time = (time.perf_counter() - start) * 1000

        # 格式化结果
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })

        logger.info(
            "检索完成",
            query=query[:50],
            n_results=len(formatted_results),
            embed_time_ms=round(embed_time, 2),
            total_time_ms=round(search_time, 2),
        )

        # 记录 Prometheus 指标
        if formatted_results:
            record_rag_hit(query_type="semantic_search")

        return formatted_results

    def delete(self, ids: list[str]) -> int:
        """
        删除文档

        Args:
            ids: 文档 ID 列表

        Returns:
            删除的数量
        """
        collection = self.get_collection()
        collection.delete(ids=ids)
        logger.info("文档已删除", count=len(ids))
        return len(ids)

    def clear(self) -> None:
        """清空集合"""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("集合已清空", collection_name=self.collection_name)
        except Exception as e:
            logger.warning("清空集合失败", error=str(e))

    def count(self) -> int:
        """获取文档数量"""
        return self.get_collection().count()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        collection = self.get_collection()
        return {
            "collection_name": self.collection_name,
            "count": collection.count(),
            "persist_dir": self.persist_dir,
        }


# 全局索引器实例
_indexer: ChromaIndexer | None = None


def get_indexer() -> ChromaIndexer:
    """获取全局索引器实例"""
    global _indexer
    if _indexer is None:
        _indexer = ChromaIndexer()
    return _indexer
