"""
知识库文档加载器
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.utils import get_logger

logger = get_logger(__name__)


class KnowledgeLoader:
    """
    知识库文档加载器

    支持:
    - Markdown 文档 (带 frontmatter)
    - 文本文件
    - 语义分割
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        初始化加载器

        Args:
            chunk_size: 分块大小 (字符)
            chunk_overlap: 分块重叠 (字符)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_markdown(self, file_path: str | Path) -> list[dict[str, Any]]:
        """
        加载 Markdown 文件

        Args:
            file_path: 文件路径

        Returns:
            文档块列表
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning("文件不存在", path=str(file_path))
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 frontmatter
        metadata = {
            "source": str(file_path.name),
            "file_path": str(file_path),
        }

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict):
                        metadata.update(frontmatter)
                    content = parts[2].strip()
                except yaml.YAMLError:
                    pass

        # 分割文档
        chunks = self._split_content(content)

        # 添加元数据
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "page_content": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
            documents.append(doc)

        logger.info(
            "Markdown 文档已加载",
            path=str(file_path),
            chunks=len(documents),
        )

        return documents

    def load_text(self, file_path: str | Path) -> list[dict[str, Any]]:
        """
        加载纯文本文件

        Args:
            file_path: 文件路径

        Returns:
            文档块列表
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {
            "source": str(file_path.name),
            "file_path": str(file_path),
        }

        chunks = self._split_content(content)

        return [
            {
                "page_content": chunk,
                "metadata": {**metadata, "chunk_index": i},
            }
            for i, chunk in enumerate(chunks)
        ]

    def load_directory(
        self,
        directory: str | Path,
        patterns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        加载目录下的所有文档

        Args:
            directory: 目录路径
            patterns: 文件模式列表 (默认 ["*.md", "*.txt"])

        Returns:
            文档块列表
        """
        directory = Path(directory)

        if not directory.exists():
            logger.warning("目录不存在", path=str(directory))
            return []

        if patterns is None:
            patterns = ["*.md", "*.txt"]

        all_documents = []

        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.suffix == ".md":
                    docs = self.load_markdown(file_path)
                else:
                    docs = self.load_text(file_path)

                all_documents.extend(docs)

        logger.info(
            "目录已加载",
            path=str(directory),
            total_documents=len(all_documents),
        )

        return all_documents

    def _split_content(self, content: str) -> list[str]:
        """
        语义分割内容

        Args:
            content: 原始内容

        Returns:
            分块列表
        """
        if not content:
            return []

        # 先按段落分割
        paragraphs = re.split(r"\n\s*\n", content)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前块 + 新段落不超过大小，则合并
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)

                # 如果段落本身超过大小，需要进一步分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(para)
                    chunks.extend(sub_chunks[:-1] if len(sub_chunks) > 1 else sub_chunks)
                    current_chunk = sub_chunks[-1] if len(sub_chunks) > 1 else ""
                else:
                    current_chunk = para

        # 保存最后一块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_paragraph(self, text: str) -> list[str]:
        """
        分割过长的段落

        Args:
            text: 长文本

        Returns:
            分块列表
        """
        chunks = []

        # 按句子分割
        sentences = re.split(r"(?<=[。！？.!?])\s*", text)

        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
