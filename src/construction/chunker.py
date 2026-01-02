# -*- coding: utf-8 -*-

"""
Chunk splitter with overlap.

Features:
- Read a text file
- Split into chunks with configurable overlap
- Output: JSONL
- CLI controllable

Examples:
  # split by characters: chunk 1000 chars, overlap 200 chars
  python chunker.py -i input.json --chunk-size 1000 --overlap 200 --out-dir out_chunks
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional


@dataclass
class Chunk:
    chunk_id: int
    text: str
    source: str
    start: int  # start offset (char index or word index)
    end: int    # end offset (exclusive)


def read_text_file(path: str, encoding: str = "utf-8") -> str:
    # Fallback reading: try encoding, then utf-8-sig, then latin-1
    tried = []
    for enc in [encoding, "utf-8-sig", "latin-1"]:
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except Exception as e:
            tried.append((enc, str(e)))
    # last resort: read with replacement
    with open(path, "r", encoding=encoding, errors="replace") as f:
        return f.read()


def split_with_overlap_indices(n_items: int, chunk_size: int, overlap: int) -> Iterable[Tuple[int, int]]:
    """
    Generate (start, end) windows over [0, n_items), each window length <= chunk_size,
    sliding by step = chunk_size - overlap.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be < chunk_size (otherwise step <= 0)")

    step = chunk_size - overlap
    start = 0
    while start < n_items:
        end = min(start + chunk_size, n_items)
        yield start, end
        if end == n_items:
            break
        start += step

def chunk_text_words(text: str, chunk_size: int, overlap: int, drop_empty: bool = True) -> List[Chunk]:
    # Simple whitespace tokenization. If you need more sophisticated tokenization, swap this out.
    words = text.split()
    chunks: List[Chunk] = []
    for idx, (s, e) in enumerate(split_with_overlap_indices(len(words), chunk_size, overlap)):
        piece_words = words[s:e]
        piece = " ".join(piece_words)
        if drop_empty and not piece.strip():
            continue
        chunks.append(Chunk(chunk_id=idx, text=piece, source="", start=s, end=e))
    return chunks


def write_jsonl(chunks: List[Chunk], out_path: str, source_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            obj = {
                "chunk_id": c.chunk_id,
                "source": source_path,
                "start": c.start,
                "end": c.end,
                "text": c.text,
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_json_dir(chunks: List["Chunk"], out_dir: str, source_path: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(source_path))[0]

    for c in chunks:
        filename = f"{base}.chunk_{c.chunk_id:05d}.json"
        path = os.path.join(out_dir, filename)

        payload = {
            "chunk_id": c.chunk_id,
            "text": c.text,
            # 如果你前面有设置：c.source = args.input
            "source": getattr(c, "source", source_path),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Split an input text file into overlapping chunks.")
    p.add_argument("-i", "--input", required=True, help="Input file path (text).")
    p.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8).")
    p.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in unit (default: 1000).")
    p.add_argument("--overlap", type=int, default=200, help="Overlap size in unit (default: 200).")
    p.add_argument("--keep-empty", action="store_true", help="Keep chunks that are empty/whitespace.")
    p.add_argument("--out-dir", default="", help="Output directory (one file per chunk).")
    return p


def main() -> None: # -> None 叫返回值类型标注（type hint / return annotation），
                    # 意思是这个函数 main 不应该返回任何值，通常对应在函数里要么 return 不写东西、要么根本不写 return，运行到末尾自然结束。
                    # 这只是“标注”，不是强制规则
                    # 运行时不会因为你写了 -> None 就阻止 return 123；它主要给 IDE、静态类型检查器（比如 mypy/pyright）和读代码的人看的。
    args = build_arg_parser().parse_args() # 读命令参数
    text = read_text_file(args.input, encoding=args.encoding) # 读文件名
    drop_empty = not args.keep_empty # 是否清空

    chunks = chunk_text_words(text, args.chunk_size, args.overlap, drop_empty=drop_empty)

    # attach source
    for c in chunks:
        c.source = args.input # 记录来源

    if args.out_dir:
        write_json_dir(chunks, args.out_dir, args.input)

    # If user didn't specify any outputs, print a brief summary + first chunk to stdout.
    if not args.out_dir:
        print(f"Generated {len(chunks)} chunks from {args.input}")
        if chunks:
            c0 = chunks[0]
            print(f"\nFirst chunk: id={c0.chunk_id}, range=[{c0.start}, {c0.end})\n")
            print(c0.text[:1000])


if __name__ == "__main__":
    main()
