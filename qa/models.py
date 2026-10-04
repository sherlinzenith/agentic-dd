from dataclasses import dataclass
from typing import List


@dataclass
class DocumentChunk:
    document: str
    page: int
    text: str
    chunk_id: str


@dataclass
class RetrievedChunk:
    document: str
    page: int
    text: str
    chunk_id: str
    score: float


@dataclass
class QAAnswer:
    answer: str
    sources: List[RetrievedChunk]