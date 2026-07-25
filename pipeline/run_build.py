"""Ingest the account corpus with Memora, run a naive-RAG baseline, export static JSON.

This is the whole experiment. Three retrieval conditions answer the same six questions
with the same model and the same answer prompt — only the retrieved context differs:

  memora   — Memora's policy-guided retriever (cue-anchor traversal, `advance_query`)
  rag      — a conventional chunk-and-embed baseline over the same notes, same embedder
  full     — every note concatenated, no retrieval at all (the correctness ceiling)

Everything the static site renders is written to ../docs/data/ by this script. The site
is a pure viewer; no inference happens at page load.

Run:  GEMINI_API_KEY=... python run_build.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from memora_gemini import install

install()  # must precede any memora import

import chromadb  # noqa: E402
import tiktoken  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402
from openai import OpenAI  # noqa: E402

from memora.memora_client import MemoraClient  # noqa: E402

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
OUT = HERE.parent / "docs" / "data"
STORE = HERE / ".memory_store"

CHAT_MODEL = "gemini-3.6-flash"
EMBED_MODEL = "gemini-embedding-001"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

TOP_K = 6
RAG_CHUNK_CHARS = 700

# tiktoken is an OpenAI tokenizer; Gemini's differs. Token counts here are a consistent
# relative measure across the three conditions, not exact Gemini billing counts.
ENC = tiktoken.get_encoding("cl100k_base")

ANSWER_PROMPT = """You are an account intelligence assistant. Answer the question using \
ONLY the context below.

Facts about this account changed over time. If the context contains multiple conflicting \
values, state what is true NOW and note what it changed from. If the context does not \
contain enough information to be sure, say so explicitly rather than guessing.

Be specific: include exact figures, dates, and names. Answer in 2-4 sentences.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

JUDGE_PROMPT = """You are grading an answer against a reference answer.

QUESTION: {question}
REFERENCE (correct): {reference}
CANDIDATE: {candidate}

The key test: does the candidate identify the CURRENT state correctly? Stating a \
superseded/outdated value as if it were current is a failure, even if the answer is \
otherwise well written.

Reply with a JSON object only:
{{"verdict": "correct" | "partial" | "wrong", "reason": "<one short sentence>"}}"""


def tokens(text: str) -> int:
    return len(ENC.encode(text or ""))


def client() -> OpenAI:
    key = os.environ["GEMINI_API_KEY"]
    return OpenAI(api_key=key, base_url=GEMINI_BASE)


def make_cfg() -> OmegaConf:
    return OmegaConf.create(
        {
            "llm": {"model": CHAT_MODEL, "seed": 42},
            "openai": {
                "api_type": "openai",
                "api_key": "shimmed-see-memora_gemini",
                "model": CHAT_MODEL,
                "embedding_model": EMBED_MODEL,
            },
            "memory": {
                "memory_store": "northwind",
                "persist_path": str(STORE),
                "collection_name": "account_memory",
                "distance": "cosine",
                "query_score_threshold": 0.3,
                "update_score_threshold": 0.8,
                "force_rebuild": True,
                "enhance_query": False,
                "return_history": True,
                "multimodal_support": False,
                "top_k": TOP_K,
                "cue_top_k": TOP_K,
                "enable_hybrid_search": False,
                "enable_segmentation": False,
                "enable_episodic_memory": False,
                "use_segments_as_episodic": False,
                "enable_cue_index": True,
            },
            "retrieval": {"strategy": "prompt"},
            "eval": {"max_workers": 4},
        }
    )


def load_notes() -> list[dict]:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    for note in manifest:
        note["text"] = (CORPUS / note["file"]).read_text()
    return manifest


# --------------------------------------------------------------------------- Memora


def build_memora(notes: list[dict]) -> tuple[MemoraClient, list[dict]]:
    if STORE.exists():
        shutil.rmtree(STORE)

    mc = MemoraClient(cfg=make_cfg(), user_id="northwind_account")

    ingested = []
    for note in notes:
        t0 = time.time()
        entries = mc.add(note["text"], type="doc")
        elapsed = time.time() - t0
        ingested.append({"file": note["file"], "date": note["date"], "entries": len(entries)})
        print(f"  {note['date']}  {note['file']:<38} {len(entries):>2} memories  {elapsed:>5.1f}s")

    return mc, ingested


def split_cues(raw) -> list[str]:
    """Memora stores cue anchors as a '||'-delimited string."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [c.strip() for c in raw if c and c.strip()]
    return [c.strip() for c in str(raw).split("||") if c.strip()]


def export_memories(mc: MemoraClient) -> list[dict]:
    entries = mc.list_memories(limit=1000)
    out = []
    for i, e in enumerate(entries):
        out.append(
            {
                "id": f"m{i}",
                "abstraction": e.index or "",
                "cues": split_cues(e.cue_indices),
                "value": e.value or "",
                "memory_type": e.memory_type or "factual",
                "timestamp": e.timestamp or e.creation_time or "",
                "history": e.history or [],
            }
        )
    return out


def cue_graph(memories: list[dict]) -> dict:
    """Edges between memories that share a cue anchor — Memora's alternate retrieval paths."""
    by_cue: dict[str, list[str]] = {}
    for m in memories:
        for cue in m["cues"]:
            by_cue.setdefault(cue.lower(), []).append(m["id"])

    edges = []
    seen = set()
    for cue, ids in by_cue.items():
        if len(ids) < 2:
            continue
        for a in ids:
            for b in ids:
                if a >= b:
                    continue
                key = (a, b)
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"source": a, "target": b, "cue": cue})
    return {"edges": edges, "shared_cues": sum(1 for v in by_cue.values() if len(v) > 1)}


# ------------------------------------------------------------------------ RAG baseline


def chunk(text: str, size: int = RAG_CHUNK_CHARS) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def build_rag(notes: list[dict], oai: OpenAI):
    path = HERE / ".rag_store"
    if path.exists():
        shutil.rmtree(path)
    db = chromadb.PersistentClient(path=str(path))
    col = db.create_collection("rag_baseline", metadata={"hnsw:space": "cosine"})

    docs, ids, metas = [], [], []
    for note in notes:
        for j, c in enumerate(chunk(note["text"])):
            docs.append(c)
            ids.append(f"{note['file']}#{j}")
            metas.append({"file": note["file"], "date": note["date"]})

    embeds = []
    for i in range(0, len(docs), 32):
        batch = docs[i : i + 32]
        resp = oai.embeddings.create(input=batch, model=EMBED_MODEL)
        embeds.extend([d.embedding for d in resp.data])

    col.add(ids=ids, documents=docs, embeddings=embeds, metadatas=metas)
    print(f"  RAG baseline: {len(docs)} chunks from {len(notes)} notes")
    return col


def rag_query(col, oai: OpenAI, question: str, k: int = TOP_K) -> list[dict]:
    qe = oai.embeddings.create(input=[question], model=EMBED_MODEL).data[0].embedding
    res = col.query(query_embeddings=[qe], n_results=k)
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({"text": doc, "file": meta["file"], "date": meta["date"], "score": round(1 - dist, 4)})
    return out


# ---------------------------------------------------------------------------- answering


def answer(oai: OpenAI, question: str, context: str) -> str:
    resp = oai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": ANSWER_PROMPT.format(context=context, question=question)}],
    )
    return (resp.choices[0].message.content or "").strip()


def judge(oai: OpenAI, question: str, reference: str, candidate: str) -> dict:
    resp = oai.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "user",
                "content": JUDGE_PROMPT.format(question=question, reference=reference, candidate=candidate),
            }
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "unparsed", "reason": raw[:200]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    oai = client()
    notes = load_notes()
    print(f"Corpus: {len(notes)} notes\n")

    print("Ingesting with Memora (Gemini-backed)...")
    mc, ingested = build_memora(notes)
    memories = export_memories(mc)
    graph = cue_graph(memories)
    print(f"  -> {len(memories)} memories, {len(graph['edges'])} cue edges\n")

    print("Building RAG baseline...")
    col = build_rag(notes, oai)

    full_context = "\n\n---\n\n".join(n["text"] for n in notes)
    ground_truth = json.loads((HERE / "ground_truth.json").read_text())

    print("\nAnswering queries under three conditions...")
    results = []
    for gt in ground_truth:
        q = gt["question"]
        print(f"\n  Q[{gt['id']}] {q}")

        t0 = time.time()
        mem_hits = mc.advance_query(q, top_k=TOP_K, query_type="prompt")
        mem_latency = round(time.time() - t0, 2)

        mem_entries = [
            {
                "abstraction": e.index or "",
                "cues": split_cues(e.cue_indices),
                "value": e.value or "",
                "score": round(e.score, 4) if isinstance(e.score, (int, float)) else None,
            }
            for e in mem_hits
        ]
        mem_context = "\n".join(f"- {e['value']}" for e in mem_entries)
        rag_hits = rag_query(col, oai, q)
        rag_context = "\n\n".join(f"[{h['file']}]\n{h['text']}" for h in rag_hits)

        conditions = {}
        for name, ctx in (("memora", mem_context), ("rag", rag_context), ("full", full_context)):
            a = answer(oai, q, ctx)
            v = judge(oai, q, gt["answer"], a)
            conditions[name] = {
                "answer": a,
                "context_tokens": tokens(ctx),
                "verdict": v.get("verdict"),
                "reason": v.get("reason"),
            }
            print(f"    {name:<7} {tokens(ctx):>6} tok  {v.get('verdict')}")

        results.append(
            {
                **gt,
                "memora_entries": mem_entries,
                "memora_latency_s": mem_latency,
                "rag_chunks": rag_hits,
                "conditions": conditions,
            }
        )

    stats = {
        "corpus": {
            "notes": len(notes),
            "signal_notes": sum(1 for n in notes if not n.get("distractor")),
            "distractor_notes": sum(1 for n in notes if n.get("distractor")),
            "words": sum(n["words"] for n in notes),
            "tokens": tokens(full_context),
            "date_range": [notes[0]["date"], notes[-1]["date"]],
        },
        "small_corpus_note": (
            "An earlier run used only the 14 account notes — 2,730 tokens total. Every condition, "
            "including no-retrieval-at-all, scored 6/6. That was an artifact of scale, not a result: "
            "with the whole corpus that small, retrieval barely had to work. Six distractor accounts "
            "discussing the same budgets, dates, sponsors and integrations were added so the right "
            "facts have to be found rather than stumbled into. Both runs are reported in the repo."
        ),
        "memora": {
            "memories": len(memories),
            "cue_anchors": sum(len(m["cues"]) for m in memories),
            "cue_edges": len(graph["edges"]),
            "shared_cues": graph["shared_cues"],
            "per_note": ingested,
        },
        "models": {"chat": CHAT_MODEL, "embedding": EMBED_MODEL, "provider": "Gemini (OpenAI-compatible endpoint)"},
        "memora_commit": "dec3f8f2444eace7004fc084abe1be9f3d88270e",
        "token_note": "Counted with tiktoken cl100k_base for a consistent relative comparison; Gemini's tokenizer differs, so these are not exact billing counts.",
        "scoreboard": {
            cond: {
                v: sum(1 for r in results if r["conditions"][cond]["verdict"] == v)
                for v in ("correct", "partial", "wrong")
            }
            for cond in ("memora", "rag", "full")
        },
        "avg_context_tokens": {
            cond: round(sum(r["conditions"][cond]["context_tokens"] for r in results) / len(results))
            for cond in ("memora", "rag", "full")
        },
    }

    (OUT / "memories.json").write_text(json.dumps(memories, indent=2))
    (OUT / "graph.json").write_text(json.dumps(graph, indent=2))
    (OUT / "queries.json").write_text(json.dumps(results, indent=2))
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    (OUT / "corpus.json").write_text(
        json.dumps([{k: n[k] for k in ("file", "date", "title", "text")} for n in notes], indent=2)
    )

    print("\n=== SCOREBOARD ===")
    for cond, sc in stats["scoreboard"].items():
        print(f"  {cond:<7} correct={sc['correct']} partial={sc['partial']} wrong={sc['wrong']}"
              f"  avg ctx={stats['avg_context_tokens'][cond]} tok")
    print(f"\nWrote 5 JSON files to {OUT}")


if __name__ == "__main__":
    main()
