"""Run Microsoft Research's Memora on Gemini instead of OpenAI/Azure OpenAI.

Memora (https://github.com/microsoft/Memora, ICML 2026) ships wired to OpenAI and
Azure OpenAI only. Nothing about its *design* is OpenAI-specific — it just calls the
`openai` SDK with no `base_url`, so it can't be pointed anywhere else. Gemini exposes
an OpenAI-compatible endpoint, so four small shims are enough to run it as-is.

Import this module BEFORE importing anything from `memora`:

    from memora_gemini import install
    install()
    from memora.memora_client import MemoraClient

The four shims, and why each is needed (all verified empirically, see ARCHITECTURE.md):

1. STUB HEAVY IMPORTS. `memora.utils.llm` and `memora.retriever.local_policy_retriever`
   import torch/transformers/peft at module top level, even though those are only used
   on the local-HuggingFace and GRPO code paths. On the hosted-API path they are ~2GB of
   dead weight. We register stub modules so the imports succeed and never get touched.

2. BASE URL. `get_openai_chat_completion_client` and `get_openai_embedding_client`
   construct `OpenAI(api_key=...)` with no `base_url`. We re-point both at Gemini's
   OpenAI-compatible endpoint.

3. MODEL TYPE ROUTING. `ChatCompletionModel._determine_model_type` decides "is this a
   hosted API model or a local HF checkpoint?" by substring-matching gpt/o1/o3. A model
   named `gemini-*` falls through to "huggingface" and Memora tries to download a
   checkpoint. We force the hosted-API path.

4. SEED. Memora always passes `seed=` to chat completions. Gemini's compatibility layer
   rejects unknown fields with a 400. We strip it in a thin client proxy.
"""

from __future__ import annotations

import os
import sys
import types

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Memora imports these at module scope but only uses them for local checkpoints.
_HEAVY_MODULES = ("torch", "transformers", "peft")

_installed = False


def _stub_heavy_modules() -> list[str]:
    """Register do-nothing stand-ins for torch/transformers/peft.

    Only stubs modules that aren't genuinely installed, so a GPU environment that does
    have them keeps the real ones. Any attribute access returns another stub, so
    Memora's `from transformers import AutoModelForCausalLM` style imports resolve.
    """

    class _Stub(types.ModuleType):
        def __getattr__(self, name):  # noqa: D105 - any attribute resolves to a stub
            if name.startswith("__") and name.endswith("__"):
                raise AttributeError(name)
            return _Stub(f"{self.__name__}.{name}")

    stubbed = []
    for name in _HEAVY_MODULES:
        if name in sys.modules:
            continue
        try:
            __import__(name)
        except ImportError:
            sys.modules[name] = _Stub(name)
            stubbed.append(name)
    return stubbed


def _gemini_client(api_key: str | None = None):
    from openai import OpenAI

    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set to run Memora against Gemini.")
    return _SeedStripper(OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL))


class _SeedStripper:
    """Proxy an OpenAI client, dropping the `seed` kwarg Gemini rejects.

    Memora hardcodes `seed=cfg.llm.seed` on every chat completion. Gemini's OpenAI
    compatibility layer returns 400 `Unknown name "seed"` rather than ignoring it, so we
    intercept the terminal `create`/`parse` calls and strip it. Everything else passes
    through untouched.
    """

    _WRAPPED_CALLS = ("create", "parse")
    _PROXIED_ATTRS = ("chat", "completions", "beta", "embeddings")

    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if name in self._WRAPPED_CALLS and callable(attr):

            def _call(*args, **kwargs):
                kwargs.pop("seed", None)
                return attr(*args, **kwargs)

            return _call
        if name in self._PROXIED_ATTRS:
            return _SeedStripper(attr)
        return attr


def install(api_key: str | None = None) -> None:
    """Apply all four shims. Safe to call more than once."""
    global _installed
    if _installed:
        return

    stubbed = _stub_heavy_modules()

    from memora.utils import embedding as memora_embedding
    from memora.utils import llm as memora_llm

    # Shim 2: point both the chat and embedding clients at Gemini.
    memora_llm.get_openai_chat_completion_client = lambda cfg: _gemini_client(api_key)
    memora_embedding.get_openai_embedding_client = lambda cfg: _gemini_client(api_key)

    # Shim 3: never route a gemini-* model name to the local HuggingFace loader.
    memora_llm.ChatCompletionModel._determine_model_type = lambda self, model_name: "azure"

    _installed = True
    if stubbed:
        print(f"[memora_gemini] stubbed unused heavy deps: {', '.join(stubbed)}")
    print(f"[memora_gemini] Memora pointed at {GEMINI_BASE_URL}")
