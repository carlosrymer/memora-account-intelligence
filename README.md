# Memory X-ray — Memora on a B2B account

**Try it live: [https://carlosrymer.github.io/memora-account-intelligence/](https://carlosrymer.github.io/memora-account-intelligence/)**

Six months of meeting notes for one B2B account, where the budget changed three times, the
go-live date twice, and the signoff owner left and came back. This runs Microsoft
Research's **Memora** over that history and asks the question an account team actually
has — *what is true right now?* — head-to-head against a conventional RAG baseline.

## What this showcases

**Technology:** [Memora](https://github.com/microsoft/Memora) — a harmonic memory
representation for long-horizon agents, presented by Microsoft Research at **ICML 2026**
([paper](https://arxiv.org/abs/2602.03315)).

Memora's claim is that agent memory does not have to choose between abstraction and
specificity. Every memory is stored in three parts:

- a **primary abstraction** — a short phrase, and the *only* thing that gets embedded
- the **memory value** — the full detail, stored whole and never summarized
- **cue anchors** — extra handles that provide alternate routes back to the memory

Retrieval then traverses those cue anchors under a learned or prompted policy rather than
leaning on vector similarity alone. The paper reports state-of-the-art results on LoCoMo
(86.3%) and LongMemEval (87.4%) while cutting token consumption by up to 98%.

That is a testable claim, so this build tests it: same corpus, same embedder, same
answering model and prompt across three retrieval conditions — Memora, a chunk-and-embed
RAG baseline, and sending every note with no retrieval at all.

**What actually surprised us, in both directions:**

The representation is genuinely good. Ingest reliably produced short, well-formed
abstractions over rich values, and cue anchors that read like something a human would
index by — `Acme migration budget`, `Dana Liu migration signoff`. You can browse all of it
on the live page.

The packaging is not. Memora is a research code drop: one commit, no releases, no PyPI
package. The documented install (`pip install -e .`) **fails outright — there is no
`pyproject.toml` or `setup.py` in the repo.** It hard-imports `torch`, `transformers` and
`peft` at module load even on the hosted-API path where none are used, and it is wired to
OpenAI/Azure OpenAI with no way to set a `base_url`. Four small shims in
[`pipeline/memora_gemini.py`](pipeline/memora_gemini.py) were enough to run it unmodified
on Gemini — Memora itself is vendored at a pinned commit and never patched.

<!--RESULTS-->

## The use case

Account history is append-only. Nobody edits the January note when the budget changes in
March, so six months in you have three budget figures, two go-live dates, and two people
who have each been "the approver" — every one of them stated with equal confidence, every
one of them true *as of when it was written*.

Conventional RAG is structurally weak here: asked about the budget, it returns all three
budget figures ranked by similarity, with nothing to say which survived. Summarization is
worse — it compresses away the exact figures, clause numbers and names the answer depends
on. This is the specificity-versus-abstraction tension Memora is built for, which makes it
a fair test rather than a flattering one.

The corpus is 56 notes: 14 hand-written for the account under test, with deliberately
evolving facts, plus 42 templated notes across six *other* accounts that discuss the same
budgets, dates, sponsors and integrations with different values. Those exist because of a
result worth being explicit about — **the first version of this experiment proved
nothing.** With only the 14 account notes (2,730 tokens), Memora, RAG, and no-retrieval-
at-all all scored 6/6. At that size the task was too easy to discriminate between
anything. The distractors make retrieval have to work; the original run is preserved in
[`pipeline/result_small_corpus.json`](pipeline/result_small_corpus.json).

The six questions are the ones that get asked before a customer call: what is the current
budget cap and how did it change, who signs off right now, when is go-live, what data
residency constraints apply, which integrations are in scope, and one multi-hop question
about whether a scope change violated a budget condition set two months earlier.

## Docs

- [Architecture](ARCHITECTURE.md) — system design, components, data flow, deployment
- [PRD](PRD.md) — problem statement, scope, success criteria, honest verdict

## Running locally

Viewing the site needs nothing but a static server:

```bash
cd docs && python3 -m http.server 8000   # then open http://localhost:8000
```

Reproducing the experiment needs a `GEMINI_API_KEY`:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

# Memora has no pyproject.toml, so it is vendored by clone and used via PYTHONPATH.
git clone https://github.com/microsoft/Memora pipeline/vendor/Memora
git -C pipeline/vendor/Memora checkout dec3f8f2444eace7004fc084abe1be9f3d88270e

cd pipeline
python build_corpus.py        # 14 hand-written account notes + ground truth
python build_distractors.py   # 42 competing-account notes

export GEMINI_API_KEY=...
PYTHONPATH=vendor/Memora/src:. python run_build.py   # ~1h, writes docs/data/*.json
```

## Stack

| Layer | Choice |
|---|---|
| Memory | Memora @ `dec3f8f`, vendored unmodified |
| LLM | `gemini-3.6-flash` via Gemini's OpenAI-compatible endpoint |
| Embeddings | `gemini-embedding-001` (3072-dim) |
| Vector store | ChromaDB (one collection for Memora, one for the RAG baseline) |
| Pipeline | Python 3.10+, OpenAI SDK, tiktoken |
| Site | Hand-written HTML/CSS/vanilla JS over precomputed JSON — no framework, no build step |

Claude models were not an option for this build, for a concrete reason: Memora needs both
chat *and* embeddings from an OpenAI-compatible endpoint, and Anthropic does not expose an
OpenAI-compatible embeddings API. Gemini does, and it supports the structured-output call
(`beta.chat.completions.parse` with a Pydantic schema) that Memora's extraction step
depends on.

## Deployed via

GitHub Pages, serving `docs/` from the `main` branch. No build step and no CI workflow —
the site is static files over precomputed JSON, so a push to `main` is the whole deploy.

---
Part of the [AI Frontier Showcase](https://github.com/carlosrymer/ai-frontier-showcase-builds) —
a running log of real-world builds trialing frontier AI models and frameworks as they ship.
