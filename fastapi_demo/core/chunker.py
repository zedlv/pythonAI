import hashlib
import os
import sys
from typing import Any, Dict, List

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import ASSET_DOC_DIR
from core.ingest import DocumentChunk, ingest_file
from core.logger import logger, setup_logging
from core.perf import PerfTimer

# 储能文档分块默认参数（故障手册、运维规范）
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 150

SliceDict = Dict[str, Any]


def generate_doc_id(file_path: str) -> str:
    """基于文件路径 MD5 生成全局唯一文档 ID，同一份文档所有切片共用"""
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()


def split_single_chunk(
    doc_chunk: DocumentChunk,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[SliceDict]:
    """
    对 D1 产出的单条 DocumentChunk 执行递归分片。
    返回切片列表，每条携带完整元数据 + doc_id。
    """
    raw_text = doc_chunk.text.strip()
    if not raw_text:
        return []

    source = doc_chunk.meta.get("source")
    if not source:
        logger.warning("文档块缺少 source 元数据，跳过分片")
        return []

    doc_id = generate_doc_id(source)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    text_segments = splitter.split_text(raw_text)

    slice_result: List[SliceDict] = []
    for seg_text in text_segments:
        seg_text = seg_text.strip()
        if not seg_text:
            continue
        slice_meta = {
            "doc_id": doc_id,
            "page": doc_chunk.meta.get("page"),
            "file_type": doc_chunk.meta.get("file_type"),
            "source": source,
        }
        slice_result.append({"text": seg_text, "meta": slice_meta})
    return slice_result


def split_document(
    chunk_list: List[DocumentChunk],
    perf: PerfTimer | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[SliceDict]:
    """统一分块入口：接收 ingest 解析输出的全部文档块，批量分片"""
    total_slices: List[SliceDict] = []
    timer = perf if perf is not None else PerfTimer()

    try:
        with timer.measure("document_chunk_split"):
            for doc_chunk in chunk_list:
                try:
                    slice_list = split_single_chunk(doc_chunk, chunk_size, chunk_overlap)
                    total_slices.extend(slice_list)
                except Exception as e:
                    source = doc_chunk.meta.get("source", "unknown")
                    logger.error(f"单文档块分片失败 | source:{source} | 错误:{e}")
        logger.info(
            f"文本分片完成 | 输入文档块:{len(chunk_list)} | 产出切片:{len(total_slices)} "
            f"| chunk_size:{chunk_size} | overlap:{chunk_overlap}"
        )
    except Exception as e:
        logger.error(f"文本分片处理异常 | 错误详情:{e}")
        return []
    return total_slices


def _run_self_test() -> None:
    """D2 自测：联动 D1 ingest 解析 + D2 分片全链路验证"""
    setup_logging()
    perf = PerfTimer()

    if not os.path.isdir(ASSET_DOC_DIR):
        logger.error(f"测试素材目录不存在：{ASSET_DOC_DIR}")
        return

    for filename in sorted(os.listdir(ASSET_DOC_DIR)):
        full_path = os.path.join(ASSET_DOC_DIR, filename)
        if not os.path.isfile(full_path):
            continue

        doc_chunks = ingest_file(full_path, perf)
        if not doc_chunks:
            continue

        slice_list = split_document(doc_chunks, perf)
        if not slice_list:
            continue

        print("=" * 80)
        print(f"文档：{filename} | 文档块:{len(doc_chunks)} | 切片数:{len(slice_list)}")
        first_slice = slice_list[0]
        print(f"切片文本片段：{first_slice['text'][:120]}...")
        print(f"完整元数据：{first_slice['meta']}")

        doc_ids = {s["meta"]["doc_id"] for s in slice_list}
        print(f"doc_id 一致性：{len(doc_ids)} 个唯一值（应为 1）")

    print("\n===== 全链路分层耗时汇总 =====")
    print(perf.get_snapshot())


if __name__ == "__main__":
    _run_self_test()
