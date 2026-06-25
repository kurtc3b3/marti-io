"""
RAG Index Builder — Full Example
=================================
Covers:
  1. Chunking strategies  (fixed-size, sliding-window, semantic)
  2. Embedding            (sentence-transformers, asymmetric queries)
  3. FAISS dense index    (IndexFlatIP + IndexIVFFlat for scale)
  4. BM25 sparse index    (keyword / exact-match)
  5. Hybrid retrieval     (dense + sparse → RRF fusion)
  6. Incremental upsert   (add / update / delete without full rebuild)

Install:
  pip install faiss-cpu sentence-transformers rank_bm25 nltk

"""

from __future__ import annotations

import hashlib
import pickle
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import faiss
import nltk
import numpy as np
from nltk.tokenize import sent_tokenize
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Document:
    """Raw source document before chunking."""
    doc_id: str
    title: str
    content: str
    metadata: dict = field(default_factory=dict)

    def content_hash(self) -> str:
        """SHA-256 of content — used to detect stale chunks on upsert."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class Chunk:
    """
    A single retrievable unit.

    Interview note: the chunk is the unit of retrieval, not the document.
    You embed the chunk, store it in FAISS, and return it to the generator.
    The generator never sees the raw document — only the chunks.
    """
    chunk_id: str          # "{doc_id}::{chunk_index}"
    doc_id: str
    doc_title: str
    text: str
    chunk_index: int
    total_chunks: int
    metadata: dict = field(default_factory=dict)

    def token_count(self) -> int:
        """Rough token estimate (word count × 1.3)."""
        return int(len(self.text.split()) * 1.3)


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    method: str  # "dense" | "sparse" | "hybrid"


# ─────────────────────────────────────────────────────────────────────────────
# 2. CHUNKING STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────

class Chunker:
    """
    Three strategies compared:

    ┌──────────────────┬─────────────────────────────────┬─────────────────────────────┐
    │ Strategy         │ Pros                            │ Cons                        │
    ├──────────────────┼─────────────────────────────────┼─────────────────────────────┤
    │ Fixed-size       │ Simple, predictable token cost  │ Splits mid-sentence/concept │
    │ Sliding window   │ Prevents boundary context loss  │ Duplicate content, larger   │
    │                  │                                 │ index                       │
    │ Semantic         │ Natural boundaries, less noise  │ Variable size, needs NLTK   │
    └──────────────────┴─────────────────────────────────┴─────────────────────────────┘

    Interview question: "When would you use fixed-size vs semantic chunking?"
    Answer: fixed-size for predictable token budgets and simple pipelines;
    semantic for QA and summarization where cross-sentence context matters.
    """

    # ── 2a. Fixed-size ────────────────────────────────────────────────────────
    @staticmethod
    def fixed_size(
        doc: Document,
        chunk_size: int = 200,   # target word count per chunk
        overlap: int = 40,       # overlapping words between adjacent chunks
    ) -> list[Chunk]:
        """
        Split by word count with a sliding overlap window.

        Why overlap?
        Without overlap, a concept that straddles a boundary is split across two
        chunks. Neither chunk contains enough context on its own. Overlap ensures
        boundary content appears in at least one full-context chunk.

        Tradeoff: overlap = (overlap / chunk_size) × index size increase.
        At 20% overlap you pay ~20% more storage and embedding compute.
        """
        words = doc.content.split()
        step = chunk_size - overlap
        raw_chunks = [
            " ".join(words[i : i + chunk_size])
            for i in range(0, len(words), step)
            if words[i : i + chunk_size]  # skip empty tail
        ]

        return [
            Chunk(
                chunk_id=f"{doc.doc_id}::fixed::{i}",
                doc_id=doc.doc_id,
                doc_title=doc.title,
                text=text,
                chunk_index=i,
                total_chunks=len(raw_chunks),
                metadata={**doc.metadata, "strategy": "fixed_size", "overlap": overlap},
            )
            for i, text in enumerate(raw_chunks)
        ]

    # ── 2b. Sliding window (alias with explicit naming) ───────────────────────
    @staticmethod
    def sliding_window(
        doc: Document,
        window_words: int = 300,
        stride_words: int = 150,  # 50% overlap
    ) -> list[Chunk]:
        """
        More aggressive overlap than fixed_size.

        Useful when:
        - Answers are short but surrounded by dense context
        - You can afford 2× the index size for higher recall

        Interview note: "sliding window" and "fixed-size with overlap" are
        often used interchangeably. The distinction is degree of overlap:
        fixed-size uses ~20%, sliding window typically 50%+.
        """
        words = doc.content.split()
        raw_chunks = [
            " ".join(words[i : i + window_words])
            for i in range(0, len(words) - window_words + stride_words, stride_words)
            if words[i : i + window_words]
        ]

        return [
            Chunk(
                chunk_id=f"{doc.doc_id}::sliding::{i}",
                doc_id=doc.doc_id,
                doc_title=doc.title,
                text=text,
                chunk_index=i,
                total_chunks=len(raw_chunks),
                metadata={**doc.metadata, "strategy": "sliding_window", "stride": stride_words},
            )
            for i, text in enumerate(raw_chunks)
        ]

    # ── 2c. Semantic chunking ─────────────────────────────────────────────────
    @staticmethod
    def semantic(
        doc: Document,
        max_sentences_per_chunk: int = 5,
        min_sentences_per_chunk: int = 2,
    ) -> list[Chunk]:
        """
        Group sentences into topic-coherent chunks.

        Simple version: fixed sentence window.
        Production version: compute sentence embeddings, detect cosine similarity
        drops between adjacent sentences (similarity < threshold → new chunk).

        Interview question: "How would you detect topic boundaries?"
        Answer: embed each sentence, compute cosine similarity between adjacent
        pairs. A drop below ~0.7 cosine similarity typically signals a topic shift.
        """
        sentences = sent_tokenize(doc.content)

        # Group into windows of max_sentences, never below min_sentences
        raw_chunks: list[str] = []
        i = 0
        while i < len(sentences):
            window = sentences[i : i + max_sentences_per_chunk]
            # Avoid orphan tail chunks smaller than min_sentences
            if len(window) < min_sentences_per_chunk and raw_chunks:
                raw_chunks[-1] += " " + " ".join(window)
            else:
                raw_chunks.append(" ".join(window))
            i += max_sentences_per_chunk

        return [
            Chunk(
                chunk_id=f"{doc.doc_id}::semantic::{i}",
                doc_id=doc.doc_id,
                doc_title=doc.title,
                text=text,
                chunk_index=i,
                total_chunks=len(raw_chunks),
                metadata={**doc.metadata, "strategy": "semantic"},
            )
            for i, text in enumerate(raw_chunks)
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMBEDDING
# ─────────────────────────────────────────────────────────────────────────────

class Embedder:
    """
    Wraps sentence-transformers.

    Model choice matters:
    - "all-MiniLM-L6-v2"         → fast, 384-dim, general purpose
    - "BAAI/bge-large-en-v1.5"   → state-of-the-art, 1024-dim, asymmetric
    - "text-embedding-3-large"   → OpenAI API (not local)

    Interview note on asymmetric embeddings:
    Queries ("what is selector drift?") and documents ("Selector drift occurs
    when...") have different linguistic distributions. BGE prepends a task
    prefix: "Represent this sentence for searching relevant passages: <query>"
    for queries but NOT for documents. This asymmetry significantly improves
    retrieval precision on short queries against long passages.
    """

    BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"[Embedder] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.is_bge = "bge" in model_name.lower()
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"[Embedder] Embedding dim: {self.dim}")

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed document chunks.
        No prefix for documents — we want the raw semantic content.
        Returns float32 L2-normalized vectors (required for cosine similarity via IP).
        """
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,  # L2-normalize → dot product = cosine similarity
            show_progress_bar=len(texts) > 50,
        )
        return vecs.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a user query.
        For BGE: prepend task prefix.
        For others: embed as-is.

        Interview note: forgetting the prefix when using BGE is a common bug
        that silently degrades retrieval quality.
        """
        text = (self.BGE_QUERY_PREFIX + query) if self.is_bge else query
        vec = self.model.encode(
            [text],
            normalize_embeddings=True,
        )
        return vec[0].astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FAISS DENSE INDEX
# ─────────────────────────────────────────────────────────────────────────────

class DenseIndex:
    """
    FAISS index wrapping chunk embeddings.

    Two FAISS index types covered:

    IndexFlatIP (exact):
    - Brute-force dot-product search
    - 100% recall — never misses the true nearest neighbor
    - O(n) per query — fine up to ~500k vectors
    - Use in dev / when index fits in RAM

    IndexIVFFlat (approximate):
    - Inverted file index: divides space into nlist Voronoi cells
    - At query time, only searches nprobe cells (default 10)
    - ~10-100× faster than Flat, <5% recall loss at nprobe=64
    - Requires a training phase on representative vectors
    - Use in prod at 500k+ vectors

    Interview question: "When would you switch from Flat to IVF?"
    Answer: when query latency > SLA target, typically >500k vectors.
    At 1M × 384-dim float32: FlatIP = ~1.5GB RAM, ~50ms/query.
    IVFFlat nlist=1024, nprobe=32: ~5ms/query, 97% recall.
    """

    def __init__(self, dim: int, use_ivf: bool = False, nlist: int = 100):
        self.dim = dim
        self.use_ivf = use_ivf
        self.chunks: list[Chunk] = []
        self.chunk_id_to_faiss_idx: dict[str, int] = {}

        if use_ivf:
            # IVF requires training — can't add vectors before train()
            quantizer = faiss.IndexFlatIP(dim)
            self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
            self.trained = False
        else:
            self.index = faiss.IndexFlatIP(dim)
            self.trained = True  # Flat index needs no training

    def train(self, training_vectors: np.ndarray):
        """
        IVF only: train the cluster centroids.
        Rule of thumb: training_vectors.shape[0] >= 39 × nlist
        (FAISS recommendation: at least 30-256 × nlist samples).
        """
        if self.use_ivf and not self.trained:
            print(f"[DenseIndex] Training IVF on {len(training_vectors)} vectors...")
            self.index.train(training_vectors)
            self.trained = True

    def add(self, chunks: list[Chunk], embeddings: np.ndarray):
        """Add chunk vectors to the index. Embeddings must be float32."""
        assert self.trained, "Call train() before add() for IVF index."
        assert embeddings.shape[1] == self.dim

        start_idx = len(self.chunks)
        self.chunks.extend(chunks)
        for i, chunk in enumerate(chunks):
            self.chunk_id_to_faiss_idx[chunk.chunk_id] = start_idx + i

        self.index.add(embeddings)
        print(f"[DenseIndex] Added {len(chunks)} chunks. Total: {self.index.ntotal}")

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[RetrievalResult]:
        """
        Search for top-k nearest neighbors by inner product (= cosine similarity
        because vectors are L2-normalized).
        Returns scores in range [−1, 1]; higher = more similar.
        """
        q = query_vec.reshape(1, -1)
        scores, indices = self.index.search(q, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            results.append(RetrievalResult(
                chunk=self.chunks[idx],
                score=float(score),
                method="dense",
            ))
        return results

    def remove(self, chunk_ids: list[str]):
        """
        Hard deletion from FAISS.

        Interview note: FAISS IndexFlatIP does NOT support remove() natively.
        Options:
        1. Rebuild the index (simplest, correct, expensive at scale)
        2. Use IndexIDMap wrapper to track external IDs and call remove_ids()
        3. Soft-delete: keep a set of deleted IDs and filter results at query time

        We use option 3 here (soft delete) for simplicity.
        """
        print(f"[DenseIndex] Soft-deleting {len(chunk_ids)} chunks.")
        self._deleted = getattr(self, "_deleted", set())
        self._deleted.update(chunk_ids)

    def search_filtered(self, query_vec: np.ndarray, top_k: int = 5) -> list[RetrievalResult]:
        """Search with soft-delete filtering applied."""
        deleted = getattr(self, "_deleted", set())
        # Over-fetch to account for deleted slots
        raw = self.search(query_vec, top_k=top_k + len(deleted) + 5)
        return [r for r in raw if r.chunk.chunk_id not in deleted][:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# 5. BM25 SPARSE INDEX
# ─────────────────────────────────────────────────────────────────────────────

class SparseIndex:
    """
    BM25Okapi for keyword / lexical retrieval.

    Why keep sparse retrieval alongside dense embeddings?

    Dense embeddings are great at semantic similarity but can miss exact
    technical terms: "IndexIVFFlat", "nprobe", "Cloud Run Jobs API".
    BM25 excels at exact-match retrieval because it's frequency-based.

    Interview question: "When does BM25 outperform dense retrieval?"
    Answer:
    - Rare technical jargon, model numbers, version strings, API names
    - Languages/domains under-represented in the embedding model's training data
    - Short documents where semantic similarity collapses to noise

    BM25 parameters:
      k1 (default 1.5): term frequency saturation. Higher = more weight on TF.
      b  (default 0.75): document length normalization. b=0 disables length norm.
    """

    def __init__(self):
        self.chunks: list[Chunk] = []
        self.bm25: Optional[BM25Okapi] = None

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + lowercase tokenizer. Replace with spacy for prod."""
        return re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()

    def build(self, chunks: list[Chunk]):
        """Build BM25 corpus from scratch. O(n) — cheap to rebuild."""
        self.chunks = chunks
        corpus = [self._tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(corpus)
        print(f"[SparseIndex] Built BM25 on {len(chunks)} chunks.")

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """
        BM25 returns raw scores (unnormalized, range [0, ∞]).
        We normalize to [0, 1] for RRF fusion compatibility.
        """
        if self.bm25 is None:
            return []

        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        # Grab top-k indices by score
        top_indices = np.argsort(scores)[::-1][:top_k]

        max_score = scores[top_indices[0]] if scores[top_indices[0]] > 0 else 1.0
        return [
            RetrievalResult(
                chunk=self.chunks[idx],
                score=float(scores[idx] / max_score),  # normalize to [0,1]
                method="sparse",
            )
            for idx in top_indices
            if scores[idx] > 0
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 6. HYBRID RETRIEVAL — RRF FUSION
# ─────────────────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievalResult]],
    k: int = 60,
    top_n: int = 5,
) -> list[RetrievalResult]:
    """
    Reciprocal Rank Fusion (RRF) — the standard hybrid retrieval algorithm.

    RRF score for chunk c across all ranked lists:
        RRF(c) = Σ  1 / (k + rank_i(c))

    where rank_i(c) is the 1-indexed rank of c in list i (or ∞ if absent).

    Why RRF over score averaging?
    - Different retrieval methods return scores on incompatible scales
      (dense: cosine [-1,1], sparse: BM25 [0,∞])
    - Normalizing scores is tricky and scale-dependent
    - RRF only uses rank position — scale-invariant by construction
    - k=60 is the standard default from the original RRF paper (Cormack 2009)

    Interview question: "How would you combine BM25 and dense retrieval?"
    This is the answer. Know it cold.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}

    for result_list in ranked_lists:
        for rank, result in enumerate(result_list, start=1):
            cid = result.chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            chunk_map[cid] = result.chunk

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [
        RetrievalResult(chunk=chunk_map[cid], score=score, method="hybrid")
        for cid, score in fused
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 7. INDEX MANAGER — ORCHESTRATION + INCREMENTAL UPSERT
# ─────────────────────────────────────────────────────────────────────────────

class RAGIndexManager:
    """
    Ties everything together. Manages:
    - Building the index from scratch
    - Hybrid search (dense + sparse → RRF)
    - Incremental upsert (add / update docs without full rebuild)
    - Persistence (save/load to disk)

    Incremental upsert strategy:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  For each incoming document:                                        │
    │  1. Compute content_hash                                            │
    │  2. If doc_id not in index → ADD                                    │
    │  3. If doc_id in index AND hash changed → DELETE old + ADD new      │
    │  4. If doc_id in index AND hash same → SKIP (no change)             │
    └─────────────────────────────────────────────────────────────────────┘

    Interview note: FAISS doesn't natively support delete. The standard
    production pattern is:
    - For small indexes (<500k): full rebuild nightly, cache in Redis during day
    - For large indexes: IndexIDMap + remove_ids(), or soft-delete + periodic compaction
    """

    PERSIST_FILE = "rag_index.pkl"

    def __init__(
        self,
        embedder: Embedder,
        chunking_strategy: str = "fixed_size",   # "fixed_size" | "sliding" | "semantic"
        chunk_size: int = 200,
        overlap: int = 40,
        use_ivf: bool = False,
    ):
        self.embedder = embedder
        self.chunking_strategy = chunking_strategy
        self.chunk_size = chunk_size
        self.overlap = overlap

        self.dense_index = DenseIndex(dim=embedder.dim, use_ivf=use_ivf)
        self.sparse_index = SparseIndex()

        # Metadata store: doc_id → {hash, chunk_ids}
        self._doc_registry: dict[str, dict] = {}

    # ── Chunking dispatch ─────────────────────────────────────────────────────
    def _chunk(self, doc: Document) -> list[Chunk]:
        if self.chunking_strategy == "fixed_size":
            return Chunker.fixed_size(doc, self.chunk_size, self.overlap)
        elif self.chunking_strategy == "sliding":
            return Chunker.sliding_window(doc, self.chunk_size, self.chunk_size // 2)
        elif self.chunking_strategy == "semantic":
            return Chunker.semantic(doc)
        else:
            raise ValueError(f"Unknown strategy: {self.chunking_strategy}")

    # ── Build from scratch ────────────────────────────────────────────────────
    def build(self, documents: list[Document]):
        """Embed all docs and build both indexes from scratch."""
        print(f"\n[IndexManager] Building index from {len(documents)} documents...")
        t0 = time.time()

        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = self._chunk(doc)
            self._doc_registry[doc.doc_id] = {
                "hash": doc.content_hash(),
                "chunk_ids": [c.chunk_id for c in chunks],
            }
            all_chunks.extend(chunks)
            print(f"  → '{doc.title}': {len(chunks)} chunks ({self.chunking_strategy})")

        print(f"\n[IndexManager] Embedding {len(all_chunks)} chunks...")
        texts = [c.text for c in all_chunks]
        embeddings = self.embedder.embed_documents(texts)

        if self.dense_index.use_ivf:
            self.dense_index.train(embeddings)

        self.dense_index.add(all_chunks, embeddings)
        self.sparse_index.build(all_chunks)

        elapsed = time.time() - t0
        print(f"[IndexManager] Index built in {elapsed:.2f}s. {len(all_chunks)} total chunks.")

    # ── Incremental upsert ────────────────────────────────────────────────────
    def upsert(self, documents: list[Document]):
        """
        Add new or update changed documents without full rebuild.

        Sparse index (BM25) is rebuilt from scratch on each upsert because
        BM25 requires the full corpus for IDF computation. This is O(n) but
        cheap — BM25 construction is fast even at 100k chunks.

        Dense index uses soft-delete for changed docs, then appends new vectors.
        A hard rebuild of FAISS is recommended weekly or when deleted% > 20%.
        """
        print(f"\n[IndexManager] Upserting {len(documents)} document(s)...")

        new_chunks: list[Chunk] = []
        for doc in documents:
            new_hash = doc.content_hash()
            existing = self._doc_registry.get(doc.doc_id)

            if existing is None:
                print(f"  [ADD]    '{doc.title}'")
            elif existing["hash"] == new_hash:
                print(f"  [SKIP]   '{doc.title}' (unchanged)")
                continue
            else:
                print(f"  [UPDATE] '{doc.title}' (content changed)")
                # Soft-delete old chunks from dense index
                self.dense_index.remove(existing["chunk_ids"])

            chunks = self._chunk(doc)
            self._doc_registry[doc.doc_id] = {
                "hash": new_hash,
                "chunk_ids": [c.chunk_id for c in chunks],
            }
            new_chunks.extend(chunks)

        if new_chunks:
            texts = [c.text for c in new_chunks]
            embeddings = self.embedder.embed_documents(texts)
            self.dense_index.add(new_chunks, embeddings)

            # Rebuild BM25 from all active chunks (including existing + new)
            all_active = self._get_all_active_chunks()
            self.sparse_index.build(all_active)

    def _get_all_active_chunks(self) -> list[Chunk]:
        """Return all non-deleted chunks from the dense index."""
        deleted = getattr(self.dense_index, "_deleted", set())
        return [c for c in self.dense_index.chunks if c.chunk_id not in deleted]

    # ── Search ────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 3,
        mode: str = "hybrid",   # "dense" | "sparse" | "hybrid"
    ) -> list[RetrievalResult]:
        """
        Retrieve top-k chunks for the given query.

        mode="hybrid" is recommended for production — it consistently
        outperforms either single method on most benchmarks.
        """
        if mode == "dense":
            q_vec = self.embedder.embed_query(query)
            return self.dense_index.search_filtered(q_vec, top_k)

        elif mode == "sparse":
            return self.sparse_index.search(query, top_k)

        elif mode == "hybrid":
            q_vec = self.embedder.embed_query(query)
            dense_results = self.dense_index.search_filtered(q_vec, top_k=top_k * 2)
            sparse_results = self.sparse_index.search(query, top_k=top_k * 2)
            return reciprocal_rank_fusion([dense_results, sparse_results], top_n=top_k)

        else:
            raise ValueError(f"Unknown mode: {mode}")

    # ── Persistence ───────────────────────────────────────────────────────────
    def save(self, path: str = PERSIST_FILE):
        """
        Persist index to disk.
        FAISS index is serialized with faiss.serialize_index().
        Everything else is pickled.

        In production on GCP:
        - FAISS binary → GCS bucket
        - _doc_registry → Firestore (as you know well)
        - Trigger rebuild via Cloud Workflows on doc change events
        """
        data = {
            "chunks": self.dense_index.chunks,
            "chunk_id_to_faiss_idx": self.dense_index.chunk_id_to_faiss_idx,
            "deleted": getattr(self.dense_index, "_deleted", set()),
            "sparse_chunks": self.sparse_index.chunks,
            "doc_registry": self._doc_registry,
            "faiss_index_bytes": faiss.serialize_index(self.dense_index.index),
            "config": {
                "dim": self.embedder.dim,
                "strategy": self.chunking_strategy,
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
            },
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[IndexManager] Saved to {path}")

    def load(self, path: str = PERSIST_FILE):
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.dense_index.chunks = data["chunks"]
        self.dense_index.chunk_id_to_faiss_idx = data["chunk_id_to_faiss_idx"]
        self.dense_index._deleted = data["deleted"]
        self.dense_index.index = faiss.deserialize_index(data["faiss_index_bytes"])
        self.dense_index.trained = True
        self.sparse_index.chunks = data["sparse_chunks"]
        self.sparse_index.bm25 = BM25Okapi([
            re.sub(r"[^a-z0-9\s]", " ", c.text.lower()).split()
            for c in data["sparse_chunks"]
        ])
        self._doc_registry = data["doc_registry"]
        print(f"[IndexManager] Loaded from {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 8. DEMO
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    Document(
        doc_id="doc-1",
        title="Cloud Run Timeout Limits",
        content=(
            "Cloud Run HTTP requests have a maximum timeout of 60 minutes. "
            "When Cloud Scheduler triggers a Cloud Run service, the HTTP connection "
            "must stay open for the full duration. For long-running scraping jobs "
            "exceeding this limit, the recommended pattern is to call the Cloud Run "
            "Jobs API directly from Scheduler, which decouples job execution from "
            "the HTTP lifecycle. Long-term, migrating to Cloud Workflows provides "
            "true async orchestration without timeout constraints. Cloud Workflows "
            "supports steps, retries, and parallel branches natively."
        ),
    ),
    Document(
        doc_id="doc-2",
        title="Firestore Roles in Scraping Pipeline",
        content=(
            "Firestore serves five distinct roles in the agentic scraping system. "
            "First, it acts as a selector registry with versioning and rollback support. "
            "Second, it stores live job execution state for tracking scraper runs. "
            "Third, it maintains a human approval queue where agentic repair proposals "
            "await review. Fourth, it holds scraper operational config, enabling "
            "data-driven pipeline configuration without Terraform changes. Fifth, "
            "it stores DOM baseline fingerprints for drift detection and comparison."
        ),
    ),
    Document(
        doc_id="doc-3",
        title="Selector Drift and DOM Fingerprinting",
        content=(
            "Selector drift occurs when a target website changes its DOM structure, "
            "breaking CSS or XPath selectors. DOM fingerprinting establishes a structural "
            "baseline of key page regions. On each run, the scraper computes a new "
            "fingerprint and compares it against the baseline stored in Firestore. "
            "Significant divergence triggers a drift alert, pauses the scraper, and "
            "enqueues an agentic repair proposal in the human approval queue. "
            "The repair agent then proposes updated selectors which a human can approve."
        ),
    ),
    Document(
        doc_id="doc-4",
        title="BM25 vs Dense Retrieval",
        content=(
            "BM25 is a sparse retrieval algorithm based on term frequency and inverse "
            "document frequency. It excels at exact-match queries and technical jargon. "
            "Dense retrieval uses neural embeddings to capture semantic meaning, handling "
            "synonyms and paraphrases well. Hybrid retrieval combines both: BM25 handles "
            "exact technical terms like IndexIVFFlat or nprobe while dense handles "
            "semantic queries. Reciprocal Rank Fusion merges the two result lists using "
            "only rank position, avoiding score scale incompatibility."
        ),
    ),
]


def run_demo():
    print("=" * 60)
    print("RAG INDEX BUILDER — DEMO")
    print("=" * 60)

    # Initialize
    embedder = Embedder("all-MiniLM-L6-v2")
    manager = RAGIndexManager(
        embedder=embedder,
        chunking_strategy="fixed_size",
        chunk_size=80,   # small for demo docs
        overlap=15,
    )

    # Build
    manager.build(SAMPLE_DOCS)

    # Query comparison: dense vs sparse vs hybrid
    queries = [
        "What is the timeout limit for Cloud Run?",
        "IndexIVFFlat nprobe configuration",          # jargon — BM25 should shine
        "How does the scraper detect website changes?",
    ]

    for query in queries:
        print(f"\n{'─'*60}")
        print(f"QUERY: {query}")
        print("─" * 60)

        for mode in ("dense", "sparse", "hybrid"):
            results = manager.search(query, top_k=2, mode=mode)
            print(f"\n  [{mode.upper()}]")
            for r in results:
                snippet = r.chunk.text[:80].replace("\n", " ")
                print(f"    score={r.score:.4f}  doc='{r.chunk.doc_title}'")
                print(f"    chunk: '{snippet}...'")

    # Incremental upsert demo
    print(f"\n{'─'*60}")
    print("UPSERT DEMO")
    print("─" * 60)

    updated_doc = Document(
        doc_id="doc-1",   # same ID — triggers update
        title="Cloud Run Timeout Limits (Updated)",
        content=(
            "Cloud Run HTTP requests now support up to 60 minutes timeout. "
            "The recommended approach for jobs exceeding this limit is to use "
            "Cloud Run Jobs via the Jobs API, which is not subject to HTTP timeouts. "
            "Cloud Workflows is preferred for complex multi-step orchestration."
        ),
    )

    new_doc = Document(
        doc_id="doc-5",
        title="Redis and Memorystore",
        content=(
            "Redis via Memorystore provides sub-millisecond ephemeral state. "
            "It is used for job locks, short-lived caches, and rate-limit counters. "
            "Unlike Firestore, Redis state is non-durable. Redis complements Firestore "
            "rather than replacing it: Redis handles hot-path reads, Firestore handles "
            "authoritative durable state."
        ),
    )

    manager.upsert([updated_doc, new_doc, SAMPLE_DOCS[1]])  # doc-2 is unchanged

    # Save and reload
    print(f"\n{'─'*60}")
    print("PERSISTENCE DEMO")
    print("─" * 60)
    manager.save("/tmp/rag_index.pkl")
    manager.load("/tmp/rag_index.pkl")
    print("[OK] Save/load round-trip successful.")

    result = manager.search("Redis job lock rate limiting", top_k=1, mode="hybrid")
    if result:
        print(f"[OK] Post-reload search: '{result[0].chunk.doc_title}' (score={result[0].score:.4f})")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
