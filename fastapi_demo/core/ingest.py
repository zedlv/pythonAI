import os
import re
import sys
from typing import List

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from config import ASSET_DOC_DIR
from core.logger import logger, setup_logging
from core.perf import PerfTimer


class DocumentChunk(BaseModel):
    """标准化解析输出，对接下游分块、向量化、向量库入库"""

    text: str
    meta: dict = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


def clean_raw_text(raw_text: str) -> str:
    """过滤乱码、页眉水印、冗余换行，保留储能设备参数"""
    text = re.sub(r"\n{2,}", "\n", raw_text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"第 \d+ 页 \| 储能技术手册", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def parse_pdf(file_path: str, perf: PerfTimer | None = None) -> List[DocumentChunk]:
    """逐页提取 PDF 文本，绑定页码元数据"""
    chunk_list: List[DocumentChunk] = []
    timer = perf if perf is not None else PerfTimer()
    total_page = 0

    try:
        with timer.measure("pdf_parse_total"):
            with pdfplumber.open(file_path) as pdf_reader:
                total_page = len(pdf_reader.pages)
                for page_idx, page in enumerate(pdf_reader.pages, start=1):
                    raw_page_content = page.extract_text()
                    if not raw_page_content:
                        continue
                    clean_content = clean_raw_text(raw_page_content)
                    if not clean_content:
                        continue
                    meta_info = {
                        "source": file_path,
                        "page": page_idx,
                        "file_type": "pdf",
                    }
                    chunk_list.append(DocumentChunk(text=clean_content, meta=meta_info))
        logger.info(
            f"PDF解析成功 | 文件路径:{file_path} | 总页数:{total_page} | 产出文本块:{len(chunk_list)}"
        )
    except Exception as e:
        logger.error(f"PDF解析失败 | 文件:{file_path} | 异常详情:{e}")
        return []
    return chunk_list


def parse_md(file_path: str, perf: PerfTimer | None = None) -> List[DocumentChunk]:
    """解析 Markdown 文档，记录文件来源与类型"""
    chunk_list: List[DocumentChunk] = []
    timer = perf if perf is not None else PerfTimer()

    try:
        with timer.measure("md_parse_total"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_md_text = f.read()
            clean_content = clean_raw_text(raw_md_text)
            if not clean_content:
                return []
            meta_info = {
                "source": file_path,
                "file_type": "md",
            }
            chunk_list.append(DocumentChunk(text=clean_content, meta=meta_info))
        logger.info(
            f"MD解析成功 | 文件路径:{file_path} | 产出文本块:{len(chunk_list)}"
        )
    except Exception as e:
        logger.error(f"MD解析失败 | 文件:{file_path} | 异常详情:{e}")
        return []
    return chunk_list


def ingest_file(file_path: str, perf: PerfTimer | None = None) -> List[DocumentChunk]:
    """按后缀自动路由至 PDF / MD 解析函数"""
    if not os.path.exists(file_path):
        logger.error(f"待解析文件不存在：{file_path}")
        return []

    suffix = os.path.splitext(file_path)[-1].lower()
    if suffix == ".pdf":
        return parse_pdf(file_path, perf)
    if suffix == ".md":
        return parse_md(file_path, perf)

    logger.warning(f"不支持的文档格式，跳过解析：{file_path}")
    return []


def _run_self_test() -> None:
    """D1 本地自测：批量解析 assets/energy_storage 下样例文档"""
    setup_logging()
    perf = PerfTimer()

    if not os.path.isdir(ASSET_DOC_DIR):
        logger.error(f"测试素材目录不存在：{ASSET_DOC_DIR}")
        return

    for filename in sorted(os.listdir(ASSET_DOC_DIR)):
        full_file_path = os.path.join(ASSET_DOC_DIR, filename)
        if not os.path.isfile(full_file_path):
            continue
        chunk_result = ingest_file(full_file_path, perf)
        if chunk_result:
            print("=" * 70)
            print(f"测试文档：{filename}")
            print(f"文本片段预览：{chunk_result[0].text[:150]}...")
            print(f"绑定元数据：{chunk_result[0].meta}")

    # 异常兜底：不存在文件
    ingest_file(os.path.join(ASSET_DOC_DIR, "不存在.pdf"), perf)

    print("\n===== 文档解析分层耗时汇总 =====")
    print(perf.get_snapshot())


if __name__ == "__main__":
    _run_self_test()
