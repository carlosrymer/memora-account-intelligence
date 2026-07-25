/* Memory X-ray — viewer for the precomputed Memora experiment.
   No inference happens here. Everything was produced by pipeline/run_build.py and
   written to data/*.json; this file only renders it. */

const CONDITIONS = [
  { key: "memora", label: "Memora", color: "var(--memora)", note: "policy-guided retrieval over harmonic memory" },
  { key: "rag", label: "RAG baseline", color: "var(--rag)", note: "chunk + embed, same embedder" },
  { key: "full", label: "Full context", color: "var(--full)", note: "every note, no retrieval" },
];

const VERDICT_ICON = { correct: "✓", partial: "~", wrong: "✕" };

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (n) => n.toLocaleString("en-US");

let DATA = {};

async function load() {
  const names = ["stats", "queries", "memories", "graph"];
  const parts = await Promise.all(
    names.map((n) => fetch(`data/${n}.json`).then((r) => {
      if (!r.ok) throw new Error(`data/${n}.json → ${r.status}`);
      return r.json();
    }))
  );
  names.forEach((n, i) => (DATA[n] = parts[i]));
}

/* ------------------------------------------------------------------ hero + tiles */

function renderHero() {
  const s = DATA.stats;
  const chips = [
    `<b>${esc(s.models.chat)}</b> answering`,
    `<b>${esc(s.models.embedding)}</b> embeddings`,
    `Memora <b>@${esc(s.memora_commit.slice(0, 7))}</b>`,
    `${num(s.corpus.notes)} notes · ${s.corpus.date_range[0]} → ${s.corpus.date_range[1]}`,
  ];
  $("#heroMeta").innerHTML = chips.map((c) => `<span class="chip">${c}</span>`).join("");
}

function renderTiles() {
  const s = DATA.stats;
  const signal = s.corpus.signal_notes ?? s.corpus.notes;
  const tiles = [
    { val: num(s.corpus.notes), lbl: "meeting notes ingested", sub: `${num(signal)} for the account in question` },
    { val: num(s.memora.memories), lbl: "memories Memora built", sub: "each abstraction + value + cues" },
    { val: num(s.memora.cue_anchors), lbl: "cue anchors", sub: `${num(s.memora.shared_cues)} shared across memories` },
    { val: num(s.corpus.tokens), lbl: "tokens in the full corpus", sub: "what no-retrieval costs per question" },
  ];
  $("#tiles").innerHTML = tiles
    .map((t) => `<div class="tile"><div class="val">${t.val}</div><div class="lbl">${t.lbl}</div><div class="sub">${t.sub}</div></div>`)
    .join("");
}

/* ------------------------------------------------------------------ scoreboard */

function renderScoreboard() {
  const box = $("#scoreboard");
  box.innerHTML = "";

  CONDITIONS.forEach((c) => {
    const row = el("div", "scorerow");
    row.append(
      el("div", "scorename", `<span class="swatch" style="background:${c.color}"></span>${esc(c.label)}`)
    );

    const vr = el("div", "verdictrow");
    DATA.queries.forEach((q) => {
      const v = q.conditions[c.key].verdict;
      const chip = el("span", "vchip",
        `<span class="ico">${VERDICT_ICON[v] ?? "?"}</span>${esc(q.id.replace(/_/g, " "))}`);
      chip.dataset.v = v;
      chip.title = q.conditions[c.key].reason || "";
      vr.append(chip);
    });

    const correct = DATA.queries.filter((q) => q.conditions[c.key].verdict === "correct").length;
    vr.append(el("span", "scoretally", `${correct}/${DATA.queries.length} correct`));
    row.append(vr);
    box.append(row);
  });

  // Table view — the non-color path to the same information.
  const t = $("#scoreTable");
  const head = `<tr><th>Question</th>${CONDITIONS.map((c) => `<th>${esc(c.label)}</th>`).join("")}</tr>`;
  const rows = DATA.queries
    .map((q) => {
      const cells = CONDITIONS.map((c) => {
        const cc = q.conditions[c.key];
        return `<td>${esc(cc.verdict)}<br><span style="color:var(--text-muted)">${esc(cc.context_tokens)} tok</span></td>`;
      }).join("");
      return `<tr><td>${esc(q.question)}</td>${cells}</tr>`;
    })
    .join("");
  t.innerHTML = head + rows;
}

/* ------------------------------------------------------------------ token bars */

function renderTokenBars() {
  const avg = DATA.stats.avg_context_tokens;
  const max = Math.max(...CONDITIONS.map((c) => avg[c.key]));
  const full = avg.full;

  $("#tokenBars").innerHTML = CONDITIONS.map((c) => {
    const v = avg[c.key];
    const pct = (v / max) * 100;
    const rel = c.key === "full" ? "baseline" : `−${Math.round((1 - v / full) * 100)}% vs full context`;
    return `<div class="bar">
      <div class="barname"><span class="swatch" style="background:${c.color}"></span>${esc(c.label)}</div>
      <div class="track">
        <div class="fill" style="width:${pct}%;background:${c.color}"></div>
        <div class="dlabel">${num(v)} tok <span>· ${rel}</span></div>
      </div>
    </div>`;
  }).join("");

  $("#tokenNote").textContent = DATA.stats.token_note;
}

/* ------------------------------------------------------------------ query x-ray */

function renderQuestionPicker() {
  const box = $("#qpicker");
  box.innerHTML = "";
  DATA.queries.forEach((q, i) => {
    const b = el("button", "qbtn", esc(q.question));
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", i === 0 ? "true" : "false");
    b.onclick = () => {
      box.querySelectorAll(".qbtn").forEach((x) => x.setAttribute("aria-selected", "false"));
      b.setAttribute("aria-selected", "true");
      renderQuestion(i);
    };
    box.append(b);
  });
  renderQuestion(0);
}

function memoraCard(e) {
  const cues = (e.cues || []).map((c) => `<span class="cue">${esc(c)}</span>`).join("");
  return `<div class="mem">
    <div class="abs">${esc(e.abstraction)}</div>
    <div class="val">${esc(e.value)}</div>
    ${cues ? `<div class="cues">${cues}</div>` : ""}
  </div>`;
}

function chunkCard(c) {
  return `<div class="chunkitem">
    <div class="src">${esc(c.file)} · sim ${c.score}</div>
    <div class="txt">${esc(c.text.length > 320 ? c.text.slice(0, 320) + "…" : c.text)}</div>
  </div>`;
}

function conditionColumn(q, key, label, items, itemsLabel) {
  const c = q.conditions[key];
  return `<div class="col" data-cond="${key}">
    <div class="colhead"><h3>${esc(label)}</h3><span class="tok">${num(c.context_tokens)} context tokens</span></div>
    <p class="answer">${esc(c.answer)}</p>
    <div class="vline" data-v="${esc(c.verdict)}">
      <span class="ico">${VERDICT_ICON[c.verdict] ?? "?"}</span>
      <strong>${esc(c.verdict)}</strong>
      <span class="why">— ${esc(c.reason || "")}</span>
    </div>
    <div class="retrieved"><b>${esc(itemsLabel)}</b>${items}</div>
  </div>`;
}

function renderQuestion(i) {
  const q = DATA.queries[i];
  const memItems = q.memora_entries.map(memoraCard).join("") || `<p class="loading">No memories retrieved.</p>`;
  const ragItems = q.rag_chunks.map(chunkCard).join("") || `<p class="loading">No chunks retrieved.</p>`;

  $("#qdetail").innerHTML = `
    <div class="qhead">
      <p class="qq">${esc(q.question)}</p>
      <p class="qwhy">${esc(q.why)}</p>
      <p class="qref"><b>Reference answer</b>${esc(q.answer)}</p>
    </div>
    <div class="cols">
      ${conditionColumn(q, "memora", "Memora", memItems, `Retrieved memories (${q.memora_entries.length})`)}
      ${conditionColumn(q, "rag", "RAG baseline", ragItems, `Retrieved chunks (${q.rag_chunks.length})`)}
    </div>`;
}

/* ------------------------------------------------------------------ memory grid */

function renderMemories() {
  const mems = DATA.memories;
  const counts = new Map();
  mems.forEach((m) => m.cues.forEach((c) => counts.set(c, (counts.get(c) || 0) + 1)));

  const shared = [...counts.entries()].filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]);
  const sel = $("#cueFilter");
  sel.innerHTML =
    `<option value="">All memories (${mems.length})</option>` +
    shared.map(([c, n]) => `<option value="${esc(c)}">${esc(c)} — ${n} memories</option>`).join("");

  $("#cueHint").textContent = shared.length
    ? `${shared.length} cue anchors are shared by more than one memory — these are the alternate paths Memora traverses.`
    : "No cue anchors are shared across memories in this run.";

  const grid = $("#memgrid");
  const more = $("#memMore");
  const PAGE = 24;
  let shown = PAGE;

  const card = (m, filter) => {
    const cues = m.cues
      .map((c) => `<span class="cue"${c === filter ? ' style="border-color:var(--memora);color:var(--memora)"' : ""}>${esc(c)}</span>`)
      .join("");
    return `<div class="memcard">
      <span class="abslbl">Primary abstraction — embedded</span>
      <div class="abs">${esc(m.abstraction)}</div>
      <span class="vallbl">Memory value — stored whole</span>
      <div class="val">${esc(m.value)}</div>
      ${cues ? `<div class="cues">${cues}</div>` : ""}
    </div>`;
  };

  const draw = () => {
    const filter = sel.value;
    const matching = filter ? mems.filter((m) => m.cues.includes(filter)) : mems;
    const slice = matching.slice(0, shown);
    grid.innerHTML = slice.map((m) => card(m, filter)).join("");
    const remaining = matching.length - slice.length;
    more.innerHTML = remaining > 0
      ? `<button class="morebtn" type="button">Show ${Math.min(PAGE, remaining)} more — ${num(remaining)} of ${num(matching.length)} hidden</button>`
      : `<span class="morenote">Showing all ${num(matching.length)} ${filter ? "matching " : ""}memories.</span>`;
    const btn = more.querySelector("button");
    if (btn) btn.onclick = () => { shown += PAGE; draw(); };
  };

  sel.onchange = () => { shown = PAGE; draw(); };
  draw();
}

/* ------------------------------------------------------------------ verdict */

function renderVerdict() {
  const s = DATA.stats;
  const sc = s.scoreboard;
  const avg = s.avg_context_tokens;
  const saveFull = Math.round((1 - avg.memora / avg.full) * 100);
  const saveRag = Math.round((1 - avg.memora / avg.rag) * 100);
  const small = s.small_corpus_note;

  const boxes = [];

  boxes.push(`<div class="vbox">
    <h3>Did Memora deliver?</h3>
    <p>On this corpus Memora answered <strong>${sc.memora.correct}/${DATA.queries.length}</strong>
    questions correctly against <strong>${sc.rag.correct}/${DATA.queries.length}</strong> for the RAG
    baseline and <strong>${sc.full.correct}/${DATA.queries.length}</strong> for sending every note with no
    retrieval at all — while using <strong>${saveFull}% fewer context tokens than full context</strong>
    and ${saveRag > 0 ? `${saveRag}% fewer than RAG` : `${Math.abs(saveRag)}% more than RAG`}.</p>
    <p>The paper claims up to 98% token reduction. We measure ${saveFull}% here, on a corpus of
    ${num(s.corpus.tokens)} tokens. That gap is expected and not a knock: the claim is made against
    benchmarks with far longer histories, where full context is enormous. The reduction scales with
    how much history you have.</p>
  </div>`);

  if (small) {
    boxes.push(`<div class="vbox"><h3>The first run proved nothing — and that mattered</h3><p>${esc(small)}</p></div>`);
  }

  boxes.push(`<div class="vbox">
    <h3>What it took to run it</h3>
    <p>Memora is a research code drop, not a product. The published <code>pip install -e .</code>
    does not work — there is no <code>pyproject.toml</code> or <code>setup.py</code> in the repo, so the
    package cannot be installed as documented. It also hard-imports <code>torch</code>,
    <code>transformers</code> and <code>peft</code> at module load even on the hosted-API path where
    none of them are used, and it is wired to OpenAI and Azure OpenAI only.</p>
    <p>None of that is fatal. Four small shims — stub the unused heavy imports, set a
    <code>base_url</code>, force hosted-API model routing, drop the <code>seed</code> parameter Gemini
    rejects — were enough to run it unmodified on Gemini. The shims live in
    <code>pipeline/memora_gemini.py</code>; Memora itself is vendored at a pinned commit and not
    patched.</p>
  </div>`);

  boxes.push(`<div class="vbox">
    <h3>Where the idea earns its keep</h3>
    <p>The three-part memory is the interesting part, and you can see it in the grid above: the
    embedded abstraction is a short phrase, but the value it points at keeps every figure, name and
    clause number intact. That is the actual trade being made — you get summarization's index size
    without summarization's data loss.</p>
    <p>Read the numbers with the corpus in mind. ${num(s.corpus.notes)} notes is small next to the
    benchmarks Memora reports on, and a fictional corpus written to contain known contradictions is
    not a substitute for real account history.</p>
  </div>`);

  $("#verdict").innerHTML = boxes.join("");
}

/* ------------------------------------------------------------------ boot */

load()
  .then(() => {
    renderHero();
    renderTiles();
    renderScoreboard();
    renderTokenBars();
    renderQuestionPicker();
    renderMemories();
    renderVerdict();
  })
  .catch((err) => {
    document.querySelector("main").innerHTML =
      `<p class="loading">Could not load experiment data: ${esc(err.message)}.
       If you are viewing this locally, serve the folder over HTTP rather than opening the file directly.</p>`;
  });
