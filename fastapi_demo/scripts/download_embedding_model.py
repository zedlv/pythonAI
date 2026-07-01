#!/usr/bin/env python3
"""通过 ModelScope 下载 Embedding 模型（国内网络友好）"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from config import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_PATH


def main() -> None:
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("请先安装: pip install modelscope")
        sys.exit(1)

    cache_dir = os.path.dirname(os.path.dirname(EMBEDDING_MODEL_PATH))
    os.makedirs(cache_dir, exist_ok=True)

    print(f"开始下载: sentence-transformers/{EMBEDDING_MODEL_NAME}")
    path = snapshot_download(
        f"sentence-transformers/{EMBEDDING_MODEL_NAME}",
        cache_dir=cache_dir,
    )
    print(f"下载完成: {path}")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(path)
    vec = model.encode(["储能BMS测试"], normalize_embeddings=True)
    print(f"验证成功 | 向量维度: {len(vec[0])}")


if __name__ == "__main__":
    main()
