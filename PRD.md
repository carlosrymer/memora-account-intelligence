# PRD — Memory X-ray (Memora account intelligence)

## Problem statement

An account team's institutional memory lives in meeting notes, and meeting notes are
append-only. Nobody goes back and edits the January note when the budget changes in March.
Six months in, the account's history contains three different budget figures, two go-live
dates, and two people who have each been "the approver" — all stated with equal confidence
in their own note, all still literally true *as of when they were written*.

The question a CSM, consultant, or account manager actually needs answered is not "what
was said about the budget" but **"what is the budget now, and when did it change?"** That
is a memory problem, not a search problem. Conventional RAG is structurally bad at it: it
retrieves the chunks most similar to the query, which for "budget" means all three budget
figures, with no signal about which one survived. Summarization is worse — it compresses
away exactly the figures, clause numbers and names the answer depends on.

Memora, presented at ICML 2026, claims to resolve that tension: keep detail intact, index
only a short abstraction, and reach memories through cue anchors rather than similarity
alone. This project tests that claim on a task shaped like the real problem.

## Target user

A customer success manager, solutions consultant, or account executive who owns a B2B
account with months of accumulated history, and who needs the current state of commitments
before a call — not a summary of everything ever discussed.

## Goals

- Test whether Memora answers "what is true now" better than a conventional RAG baseline
  over the same corpus, embedder, and answering model.
- Make the harmonic memory representation *visible* — show the abstraction, the value, and
  the cue anchors as distinct things, not as an opaque retrieval score.
- Measure context cost per question against both RAG and no-retrieval-at-all.
- Establish honestly whether Memora is usable today, including everything that had to be
  worked around to run it.
- Ship it as a permanent, free-to-host public link.

## Non-goals

- Reproducing the paper's LoCoMo / LongMemEval numbers. Different corpus, different scale.
- Testing Memora's GRPO-trained retrieval policy — that needs a GPU and a training run.
- Building a real account-intelligence product. This is a demo with a fictional account.
- Live querying by visitors. The experiment is precomputed; the page is a viewer.
- Benchmarking Gemini. The model is held constant across conditions; it is not what is
  being trialed.

## Scope (MVP)

- A 56-note corpus: 14 hand-written notes for one account with deliberately evolving
  facts, plus 42 templated notes across six competing accounts as retrieval distractors.
- Six questions whose correct answers depend on knowing which version of a fact is
  current, each with a written reference answer.
- Three retrieval conditions — Memora, RAG baseline, full context — sharing one answering
  prompt and model.
- LLM-judge grading against the reference answers, with all verdicts published.
- A static page showing the scoreboard, context-token comparison, a per-question X-ray of
  what each system retrieved and answered, and a browsable view of every memory Memora
  built.

## User stories

- As an account manager, I want to ask "what is the current budget cap" and get the figure
  that is true today, so that I do not quote a superseded number on a customer call.
- As an account manager, I want to see *what changed and when*, so that I can explain the
  history rather than just assert the current value.
- As an engineer evaluating memory frameworks, I want to see exactly what was retrieved
  under each condition, so that I can judge whether the win is real or prompt-driven.
- As an engineer, I want to know what it actually took to run this library, so that I can
  estimate the cost of adopting it.

## Success criteria

Two things had to be true for this to count as a fair trial.

**1. Memora had to actually run, and actually do the memory work.** It does. Memora at
commit `dec3f8f` built the memory store, produced the abstractions and cue anchors, and
served retrieval through its own policy-guided retriever. Nothing about the memory
representation was reimplemented here.

But it did not run as documented. The published install command (`pip install -e .`)
**fails** — there is no `pyproject.toml` or `setup.py` in the repository. The library
hard-imports `torch`, `transformers` and `peft` at module load even on the hosted-API path
where none are used, and it is wired to OpenAI/Azure OpenAI with no way to set a
`base_url`. Four shims in `pipeline/memora_gemini.py` were enough to work around all of it
without editing Memora's source. Verdict: **the ideas are usable today; the packaging is
not.** Treat it as research code you vendor at a pinned commit, not a dependency you
install.

**2. The experiment had to be able to discriminate.** The first version could not, and
that is worth stating plainly. With only the 14 account notes — 2,730 tokens total —
Memora, RAG, and sending every note with no retrieval all scored 6/6. That was not
evidence for Memora; it was evidence that the task was too easy, because at that size the
answering model could reconcile the conflicting values itself. The distractor accounts
exist because of that failure, and the original result is preserved in
`pipeline/result_small_corpus.json` rather than deleted.

Final scored results, and the honest read on whether Memora beat the baseline, are on the
live page and in `docs/data/stats.json`. The token-efficiency claim (the paper reports up
to 98% reduction) is reported here as measured, at this corpus size, with the caveat that
the reduction scales with history length and this corpus is short.

## Risks / open questions

- **Corpus realism.** A fictional corpus written to contain known contradictions is a
  cleaner test than real notes would be. It may flatter any system that handles
  contradictions well, including the baseline.
- **Prompt sensitivity.** The shared answering prompt tells the model to prefer current
  values when the context conflicts. That instruction helps the RAG baseline more than it
  helps Memora, since RAG is likelier to surface conflicts. It is applied identically to
  all conditions, but a different prompt would move the numbers.
- **LLM-as-judge.** Grading is model-driven. Verdicts and reasons are published so they can
  be checked.
- **Single run, no seeds.** Gemini rejects the `seed` parameter, so runs are not
  bit-reproducible and results are from one run, not an average over several.
- **Pinned to a research commit.** Memora has one commit and no releases. The shims may
  break on any future push.

## Timeline

One sitting. Research and feasibility testing, adapter, corpus, pipeline, scaled re-run
after the first design failed to discriminate, static viewer, docs, deploy.
