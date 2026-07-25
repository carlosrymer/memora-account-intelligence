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

## Results

Six questions, three conditions, same model and prompt throughout. Graded by an LLM judge
against written reference answers, with stating a superseded value as current counted as a
failure.

| Condition | Correct | Avg context tokens |
|---|---|---|
| **Memora** (policy-guided retrieval) | **5 / 6** | **684** |
| RAG baseline (chunk + embed) | 6 / 6 | 851 |
| Full context (no retrieval) | 6 / 6 | 7,122 |

**Memora lost on accuracy.** The system under trial was beaten by the baseline it is meant
to improve on, on the task it was designed for. It won on cost — 90% fewer context tokens
than full context, 20% fewer than RAG — but that is the cheaper half of the claim.

### Why it lost, specifically

The miss was *"Which integrations are in scope for go-live?"* (answer: Salesforce and
Klaviyo). It is worth understanding, because it is the failure mode Memora's design exists
to prevent.

Retrieval was not the problem. Memora **did** surface the correct memory — one entry says
plainly that scope is Salesforce and Klaviyo. But it also surfaced a *consolidated* entry,
"migration go-live timeline, scope, and risks", which had folded the January, March and
April notes into one memory and ended by asserting go-live is *"August 15, 2026, with 1,200
seats and Salesforce-only functionality"* — stale on all three counts, stated flatly as
current, with nothing marking it superseded.

Two retrieved memories contradicted each other; the answer split the difference and got it
wrong. Consolidating related updates into unified entries is the mechanism that makes the
memory scale, and here it is what manufactured the error. The RAG baseline, which keeps
chunks dated and separate, had an easier time telling old from current.

### What still stands up

The three-part representation is sound and does what it says: short embedded abstractions
over values that keep every figure, name and clause number intact. That is what produces
the token saving, and you can inspect all 197 memories on the live page. The cue anchors
are better than expected — 468 of them, 29 shared across memories, reading like something a
person would index by rather than keyword spray.

The honest read is that the *representation* held up and the *consolidation policy* is
where the risk sits. On a corpus whose defining feature is that facts get superseded,
merging updates without preserving which value won is the thing that bites.

### How much to read into it

Not a lot, in either direction. One run, no averaging, 56 notes, 6 questions, a fictional
corpus built to contain known contradictions. A single wrong answer is the difference
between "loss" and "tie". At 7,122 tokens the whole corpus still fits in context, which is
well below the scale Memora targets — on LoCoMo/LongMemEval-sized histories, full context
stops being an option and the token argument gets much stronger than it looks here.

Every answer, verdict, and retrieved memory is published in
[`docs/data/queries.json`](docs/data/queries.json) so the grading can be checked by hand.

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
