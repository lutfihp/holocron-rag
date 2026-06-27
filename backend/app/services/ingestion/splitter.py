from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter


def split_text(text: str, *, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Sentence-aware splitter via LlamaIndex.

    chunk_size and overlap are measured in tokens by LlamaIndex's tokenizer.
    """
    if not text.strip():
        return []
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return splitter.split_text(text)
