#!/usr/bin/env python
"""
知识库索引脚本

Usage:
    python scripts/load_knowledge.py --dir ./knowledge_base
    python scripts/load_knowledge.py --reset  # 清空后重建索引
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import ChromaIndexer, KnowledgeLoader
from app.utils import get_logger

logger = get_logger(__name__)


def load_knowledge(directory: str, reset: bool = False) -> int:
    """
    加载知识库到向量数据库

    Args:
        directory: 知识库目录
        reset: 是否清空后重建

    Returns:
        索引的文档数量
    """
    print(f"开始加载知识库: {directory}")

    # 初始化
    indexer = ChromaIndexer()
    loader = KnowledgeLoader(chunk_size=500, chunk_overlap=50)

    # 清空现有索引
    if reset:
        print("清空现有索引...")
        indexer.clear()

    # 检查当前数量
    current_count = indexer.count()
    print(f"当前索引文档数: {current_count}")

    # 加载文档
    print("加载文档...")
    documents = loader.load_directory(directory)
    print(f"加载文档块数: {len(documents)}")

    if not documents:
        print("未找到文档")
        return 0

    # 生成文档 ID
    ids = []
    for i, doc in enumerate(documents):
        source = doc.get("metadata", {}).get("source", "unknown")
        chunk_index = doc.get("metadata", {}).get("chunk_index", i)
        ids.append(f"{source}_{chunk_index}")

    # 添加到索引
    print("索引文档中...")
    added = indexer.add_documents(documents, ids=ids)

    # 统计
    final_count = indexer.count()
    print(f"索引完成: {added} 个文档块")
    print(f"总文档数: {final_count}")

    return added


def main():
    parser = argparse.ArgumentParser(description="知识库索引工具")
    parser.add_argument(
        "--dir",
        type=str,
        default="./knowledge_base",
        help="知识库目录路径",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空现有索引后重建",
    )
    args = parser.parse_args()

    try:
        load_knowledge(args.dir, args.reset)
        print("完成！")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
