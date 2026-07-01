import hashlib
import os
import sys
import time
from typing import Any, Dict, List, Optional, Protocol

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import chromadb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from config import (
    ASSET_DOC_DIR,
    COLLECTION_NAME,
    EMBED_BATCH_SIZE,
    EMBED_MAX_RETRIES,
    EMBEDDING_BACKEND,
    EMBEDDING_DIM,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_MODEL_PATH,
    MAX_TEXT_CHAR_LEN,
    TOP_N_RETRIEVE,
    VECTOR_DB_PATH,
)
from core.chunker import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, split_document
from core.ingest import ingest_file
from core.logger import logger, setup_logging
from core.perf import PerfTimer

SliceDict = Dict[str, Any]
RetrieveDict = Dict[str, Any]


class Embedder(Protocol):
    def encode(self, texts: List[str]) -> List[List[float]]: ...


class TfidfEmbedder:
    """离线回退：字符 n-gram TF-IDF，网络不可用时可完成 D3 链路验收"""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            max_features=dim,
        )
        self._fitted = False

    def encode(self, texts: List[str]) -> List[List[float]]:
        clean_texts = [truncate_text(t) for t in texts if truncate_text(t)]
        if not clean_texts:
            return []

        if not self._fitted:
            matrix = self._vectorizer.fit_transform(clean_texts)
            self._fitted = True
        else:
            matrix = self._vectorizer.transform(clean_texts)

        return _normalize_rows(matrix.toarray())


class SentenceTransformerEmbedder:
    def __init__(self, model_path_or_name: str, local_only: bool = False):
        from sentence_transformers import SentenceTransformer

        logger.info(f"加载 Embedding 模型：{model_path_or_name}")
        self._model = SentenceTransformer(
            model_path_or_name,
            local_files_only=local_only,
        )

    def encode(self, texts: List[str]) -> List[List[float]]:
        clean_texts = [truncate_text(t) for t in texts if truncate_text(t)]
        if not clean_texts:
            return []
        vecs = self._model.encode(
            clean_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.tolist()


_embedder: Embedder | None = None
_chroma_client: chromadb.PersistentClient | None = None
_collection = None


def _normalize_rows(matrix: np.ndarray) -> List[List[float]]:
    rows: List[List[float]] = []
    for row in matrix:
        norm = np.linalg.norm(row)
        if norm == 0:
            rows.append(row.tolist())
        else:
            rows.append((row / norm).tolist())
    return rows


def truncate_text(text: str) -> str:
    """超长文本截断，适配向量模型输入上限"""
    text = text.strip()
    if len(text) <= MAX_TEXT_CHAR_LEN:
        return text
    return text[:MAX_TEXT_CHAR_LEN]


def _resolve_model_source() -> tuple[str, bool]:
    """优先使用本地下载目录，避免重复访问 HuggingFace"""
    if EMBEDDING_MODEL_PATH and os.path.isdir(EMBEDDING_MODEL_PATH):
        return EMBEDDING_MODEL_PATH, True
    return EMBEDDING_MODEL_NAME, False


def get_embedder() -> Embedder:
    """按配置选择向量后端；auto 模式 ST 失败时回退 TF-IDF"""
    global _embedder
    if _embedder is not None:
        return _embedder

    backend = EMBEDDING_BACKEND.lower()
    if backend == "tfidf":
        logger.info("使用 TF-IDF 离线向量化后端")
        _embedder = TfidfEmbedder()
        return _embedder

    if backend in ("sentence-transformers", "st", "auto"):
        model_src, local_only = _resolve_model_source()
        try:
            _embedder = SentenceTransformerEmbedder(model_src, local_only=local_only)
            return _embedder
        except Exception as e:
            if backend != "auto":
                raise
            logger.warning(f"SentenceTransformer 加载失败，回退 TF-IDF | 错误:{e}")

    logger.info("使用 TF-IDF 离线向量化后端")
    _embedder = TfidfEmbedder()
    return _embedder


def get_collection():
    """懒加载 ChromaDB 集合"""
    global _chroma_client, _collection
    if _collection is None:
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        _collection = _chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def _sanitize_meta(meta: dict) -> dict:
    """ChromaDB 元数据仅支持 str/int/float/bool，且不允许 None"""
    clean: dict = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    if "page" not in clean:
        clean["page"] = -1
    return clean


def _make_slice_id(meta: dict, text: str) -> str:
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"{meta['doc_id']}_{text_hash}"


def batch_embed_texts(text_list: List[str], perf: PerfTimer) -> List[List[float]]:
    """分批生成文本向量，单批失败自动重试"""
    if not text_list:
        return []

    embedder = get_embedder()
    all_vectors: List[List[float]] = []
    total_batch = (len(text_list) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE

    with perf.measure("embedding_total"):
        for batch_idx in range(total_batch):
            start = batch_idx * EMBED_BATCH_SIZE
            end = start + EMBED_BATCH_SIZE
            batch_texts = text_list[start:end]

            last_error: Exception | None = None
            for attempt in range(1, EMBED_MAX_RETRIES + 1):
                try:
                    with perf.measure(f"embedding_batch_{batch_idx}"):
                        vecs = embedder.encode(batch_texts)
                    all_vectors.extend(vecs)
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"向量化批次失败 | batch:{batch_idx} | attempt:{attempt} | 错误:{e}"
                    )
                    time.sleep(1)
            else:
                logger.error(
                    f"向量化批次最终失败 | batch:{batch_idx} | 错误:{last_error}"
                )

    logger.info(f"批量向量化完成 | 总批次:{total_batch} | 文本总数:{len(text_list)}")
    return all_vectors


def batch_store_to_vector_db(slice_list: List[SliceDict], perf: PerfTimer) -> int:
    """将切片文本、向量、元数据批量写入向量库（upsert）"""
    if not slice_list:
        logger.warning("无待入库切片，跳过向量存储")
        return 0

    texts: List[str] = []
    metas: List[dict] = []
    ids: List[str] = []

    for slice_item in slice_list:
        text = truncate_text(slice_item["text"])
        if not text:
            continue
        meta = _sanitize_meta(slice_item["meta"])
        texts.append(text)
        metas.append(meta)
        ids.append(_make_slice_id(meta, text))

    if not texts:
        logger.warning("过滤空文本后无有效切片，跳过入库")
        return 0

    vectors = batch_embed_texts(texts, perf)
    if len(vectors) != len(texts):
        logger.error(
            f"向量数量与文本不一致 | texts:{len(texts)} | vectors:{len(vectors)}"
        )
        return 0

    collection = get_collection()
    with perf.measure("vector_db_insert"):
        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metas,
        )

    logger.info(f"向量入库成功 | 入库切片数量:{len(texts)}")
    return len(texts)


def retrieve_similar_docs(
    query: str,
    perf: PerfTimer,
    filter_doc_id: Optional[str] = None,
    top_n: int = TOP_N_RETRIEVE,
) -> List[RetrieveDict]:
    """输入问题，返回 TopN 相似储能切片，支持按 doc_id 过滤"""
    query = truncate_text(query)
    if not query:
        return []

    embedder = get_embedder()
    collection = get_collection()

    with perf.measure("query_embedding"):
        query_vec = embedder.encode([query])[0]

    where_filter = {"doc_id": filter_doc_id} if filter_doc_id else None

    with perf.measure("vector_search"):
        result = collection.query(
            query_embeddings=[query_vec],
            n_results=top_n,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

    retrieve_list: List[RetrieveDict] = []
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        retrieve_list.append(
            {
                "text": doc,
                "meta": meta,
                "similarity_distance": dist,
            }
        )
    return retrieve_list


def full_kb_import(file_path: str, perf: PerfTimer) -> int:
    """单文档完整链路：D1 解析 → D2 分片 → D3 向量化入库"""
    try:
        doc_chunks = ingest_file(file_path, perf)
        if not doc_chunks:
            logger.error(f"文档解析失败，跳过入库：{file_path}")
            return 0

        slice_list = split_document(
            doc_chunks, perf, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
        )
        if not slice_list:
            logger.warning(f"无有效文本切片：{file_path}")
            return 0

        return batch_store_to_vector_db(slice_list, perf)
    except Exception as e:
        logger.error(f"文档入库异常 | 文件:{file_path} | 错误:{e}")
        return 0


def _run_self_test() -> None:
    """D3 自测：批量导入储能样例 + 检索验证"""
    setup_logging()
    perf = PerfTimer()

    if not os.path.isdir(ASSET_DOC_DIR):
        logger.error(f"测试素材目录不存在：{ASSET_DOC_DIR}")
        return

    # 优先用核心样例验收，避免首次自测导入过多文件
    priority_files = [
        "BMS故障代码手册.pdf",
        "逆变器运维规范.md",
    ]
    test_files = [
        f for f in priority_files if os.path.isfile(os.path.join(ASSET_DOC_DIR, f))
    ]
    if not test_files:
        test_files = sorted(os.listdir(ASSET_DOC_DIR))

    total_imported = 0
    for filename in test_files:
        full_path = os.path.join(ASSET_DOC_DIR, filename)
        if not os.path.isfile(full_path):
            continue
        total_imported += full_kb_import(full_path, perf)

    print(f"\n===== 入库完成 | 总切片数:{total_imported} =====")

    test_queries = [
        "E001单体过压故障处理步骤",
        "逆变器 E101 直流过压怎么处理",
    ]
    for test_query in test_queries:
        print(f"\n===== 检索测试：{test_query} =====")
        retrieve_result = retrieve_similar_docs(test_query, perf)
        if not retrieve_result:
            print("未检索到结果")
            continue
        for idx, item in enumerate(retrieve_result):
            print(f"\n【匹配切片{idx + 1} 距离：{item['similarity_distance']:.4f}】")
            print(f"原文片段：{item['text'][:200]}...")
            print(f"完整元数据：{item['meta']}")

    bms_path = os.path.join(ASSET_DOC_DIR, "BMS故障代码手册.pdf")
    if os.path.isfile(bms_path):
        from core.chunker import generate_doc_id

        bms_doc_id = generate_doc_id(bms_path)
        print(f"\n===== doc_id 过滤检索（仅 BMS 手册）=====")
        filtered = retrieve_similar_docs(
            "单体过压触发条件",
            perf,
            filter_doc_id=bms_doc_id,
        )
        for idx, item in enumerate(filtered):
            print(f"[{idx + 1}] page={item['meta'].get('page')} | {item['text'][:120]}...")

    print("\n===== 全链路性能耗时汇总 =====")
    print(perf.get_snapshot())


if __name__ == "__main__":
    _run_self_test()
