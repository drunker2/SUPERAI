"""
阿里云 Embedding 模型封装
"""

import time
from typing import Any

import dashscope
from dashscope import TextEmbedding

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)


class QwenEmbedding:
    """
    阿里云通义千问 Embedding 模型

    使用 text-embedding-v3 模型，输出 1024 维向量
    """

    def __init__(
        self,
        model: str = "text-embedding-v3",
        batch_size: int = 10,
    ):
        """
        初始化 Embedding 模型

        Args:
            model: 模型名称
            batch_size: 批处理大小 (API 限制 10)
        """
        self.model = model
        self.batch_size = batch_size
        self.api_key = settings.dashscope_api_key

        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")

        dashscope.api_key = self.api_key

    def embed_query(self, text: str) -> list[float]:
        """
        生成单个查询的嵌入向量

        Args:
            text: 查询文本

        Returns:
            嵌入向量 (1024 维)
        """
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成文档的嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        all_embeddings = []

        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            start = time.perf_counter()

            try:
                response = TextEmbedding.call(
                    model=self.model,
                    input=batch,
                    text_type="document",
                )

                if response.status_code != 200:
                    logger.error(
                        "Embedding 调用失败",
                        status_code=response.status_code,
                        message=response.message,
                    )
                    raise RuntimeError(f"Embedding 调用失败: {response.message}")

                # 提取嵌入向量
                batch_embeddings = [item["embedding"] for item in response.output["embeddings"]]
                all_embeddings.extend(batch_embeddings)

                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    "Embedding 批处理完成",
                    batch_size=len(batch),
                    duration_ms=round(duration_ms, 2),
                )

            except Exception as e:
                logger.error("Embedding 生成异常", error=str(e))
                raise

        return all_embeddings

    async def aembed_query(self, text: str) -> list[float]:
        """异步版本的 embed_query"""
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """异步版本的 embed_documents"""
        return self.embed_documents(texts)


def get_embedding_model() -> QwenEmbedding:
    """获取 Embedding 模型单例"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = QwenEmbedding()
    return _embedding_model


# 全局实例
_embedding_model: QwenEmbedding | None = None
