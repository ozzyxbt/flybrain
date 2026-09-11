/* Dashboard renderer. Reads the hash-chained run artifacts via /api/index;
   nothing shown here comes from any other store. */
(function () {
  const $ = (s, el) => (el || document).querySelector(s);
  const h = (tag, attrs, ...kids) => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null) el.append(k.nodeType ? k : document.createTextNode(String(k)));
    return el;
  };
  const short = (s) => (s ? s.slice(0, 16) + "…" : "—");
  const CATS = ["name", "ticker", "logo", "palette", "description", "launch_venue", "launch_action"];

  function candidateLabel(manifest, cat, id) {
    if (!id) return null;
    const c = (manifest.categories[cat] || []).find((x) => x.id === id);
    if (!c) return id;
    return c.text || c.label || id;
  }

  async function parseNpy(url) {
    const buf = await (await fetch(url)).arrayBuffer();
    const view = new DataView(buf);
    const major = view.getUint8(6);
    const headerLen = major === 1 ? view.getUint16(8, true) : view.getUint32(8, true);
    const start = (major === 1 ? 10 : 12) + headerLen;
    return new Int32Array(buf.slice(start));
  }

  function drawRaster(canvas, counts) {
    const ctx = canvas.getContext("2d");
    const n = counts.length;
    const cols = Math.min(n, 512);
    canvas.width = cols;
    canvas.height = 34;
    ctx.fillStyle = "#0a0f1c";
    ctx.fillRect(0, 0, cols, 34);
    let max = 1;
    const bins = new Float32Array(cols);
    for (let i = 0; i < n; i++) bins[Math.floor((i * cols) / n)] += counts[i];
    for (let i = 0; i < cols; i++) max = Math.max(max, bins[i]);
    for (let i = 0; i < cols; i++) {
      const v = bins[i] / max;
      ctx.fillStyle = v > 0.66 ? "#bef264" : v > 0.33 ? "#38bdf8" : "#3b4b6e";
      ctx.fillRect(i, 34 - Math.round(v * 32), 1, Math.round(v * 32));
    }
  }

  function resClass(r) {
    if (!r || r === "NO_DECISION") return "nodec";
    if (r === "wait" || r === "NO_LAUNCH") return "wait";
    return "win";
  }

  async function load() {
    const idx = await (await fetch("/api/index")).json();
    const chain = idx.chain;
    const byKind = {};
    for (const e of chain) (byKind[e.kind] = byKind[e.kind] || []).push(e);
    const run = (byKind.run_header || [])[0]?.artifact;
    const trials = Object.fromEntries((byKind.trial || []).map((e) => [e.sha256, e]));
    const matches = byKind.match_result || [];
    const cats = Object.fromEntries((byKind.category_result || []).map((e) => [e.artifact.category, e]));
    const final = (byKind.final_decision || [])[0];
    const intent = (byKind.launch_intent || [])[0];
    const receipt = (byKind.launch_receipt || [])[0];
    const veto = (byKind.launch_veto || [])[0];
    return { idx, manifest: idx.manifest, run, trials, matches, cats, final, intent, receipt, veto, chain, byKind };
  }

  function headerBits(d) {
    $("#run-id").textContent = d.run ? d.run.run_id : "no run";
    const b = $("#backend");
    b.textContent = d.run ? d.run.backend : "";
    b.className = "badge " + (d.run && d.run.backend === "fixture-brain-v1" ? "warn" : "ok");
    if (d.idx.chain_error) {
      const w = $("#verify");
      w.textContent = "CHAIN BROKEN: " + d.idx.chain_error;
      w.className = "badge bad";
    }
    fetch("/api/verify").then((r) => r.json()).then((rep) => {
      const w = $("#verify");
      w.textContent = (rep.ok ? "VERIFIED " : "VERIFY FAILED ") + rep.checks.length + " checks / " + rep.failures + " failures";
      w.className = "badge " + (rep.ok ? "ok" : "bad");
      w.title = rep.checks.filter((c) => !c.ok).map((c) => c.check + " " + c.detail).join("\n");
    });
  }

  // ---------------------------------------------------------------- /choose
  async function choose() {
    const d = await load();
    headerBits(d);
    if (!d.run) return;
    const m = d.manifest;
    $("#manifest-hash").textContent = d.idx.manifest_sha256;
    $("#checkpoint-hash").textContent = d.run.checkpoint_sha256;
    $("#commit").textContent = d.run.software.git_commit;
    $("#disclosure").textContent = m.disclosure;
    const tl = $("#timeline");
    const finalId = d.final ? d.final.artifact.identity : {};
    let selected = null;
    for (const cat of CATS) {
      const c = d.cats[cat];
      let res, cls;
      if (!c) {
        res = d.final && d.final.artifact.skipped_categories.includes(cat) ? "SKIPPED" : "PENDING";
        cls = "pending";
      } else if (cat === "launch_action") {
        res = c.artifact.result;
        cls = res === "LAUNCH" ? "win" : "wait";
      } else {
        res = c.artifact.winner ? candidateLabel(m, cat, c.artifact.winner) : "NO_DECISION";
        cls = resClass(c.artifact.winner);
      }
      const step = h("div", { class: "step " + cls, onclick: () => selectCategory(cat) },
        h("div", { class: "cat" }, cat.replace("_", " ")),
        h("div", { class: "res" }, res),
        h("div", { class: "meta" }, c ? "root " + short(c.sha256) : "")
      );
      step.dataset.cat = cat;
      tl.append(step);
    }
    // commitments
    const cm = $("#commitments");
    for (const c of d.idx.commitments) {
      cm.append(h("tr", null, h("td", null, c.kind), h("td", { class: "hash" }, c.sha256), h("td", null, c.memo), h("td", null, c.signature ? h("a", { href: "#" }, c.signature) : h("span", { class: "sim" }, "LOCAL / NOT ON CHAIN"))));
    }
    // matches table
    const mt = $("#matches");
    const rows = {};
    for (const e of d.matches) {
      const a = e.artifact;
      const res = a.result === "NO_DECISION" ? "NO_DECISION" : candidateLabel(m, a.category, a.result);
      const cls = a.result === "NO_DECISION" ? "res-nodec" : a.result === "wait" ? "res-wait" : "res-win";
      const tr = h("tr", { "data-sha": e.sha256, onclick: () => showMatch(e) },
        h("td", null, a.category.replace("_", " ") + (a.header_extra ? " · " + a.header_extra : "")),
        h("td", null, "r" + a.round + " m" + a.match),
        h("td", null, candidateLabel(m, a.category, a.candidate_a) + " vs " + candidateLabel(m, a.category, a.candidate_b)),
        h("td", null, a.attempts.length + "/" + a.max_attempts),
        h("td", { class: cls }, res),
        h("td", { class: "hash" }, short(e.sha256))
      );
      rows[e.sha256] = tr;
      mt.append(tr);
    }
    function selectCategory(cat) {
      const last = [...d.matches].reverse().find((e) => e.artifact.category === cat);
      if (last) showMatch(last);
    }
    async function showMatch(e) {
      const a = e.artifact;
      for (const tr of Object.values(rows)) tr.classList.toggle("sel", tr === rows[e.sha256]);
      for (const s of tl.children) s.classList.toggle("active", s.dataset.cat === a.category);
      const box = $("#match");
      box.innerHTML = "";
      const title = h("h2", null, "MATCH · " + a.category.replace("_", " ") + " · round " + a.round + " · match " + a.match + (a.header_extra ? " · " + a.header_extra : ""));
      const resText = a.result === "NO_DECISION" ? "NO_DECISION — nobody picks" : "winner: " + candidateLabel(m, a.category, a.result) + " (" + a.result + ")";
      box.append(title, h("div", { class: "big", style: "font-size:20px" }, candidateLabel(m, a.category, a.candidate_a) + "  vs  " + candidateLabel(m, a.category, a.candidate_b)),
        h("div", { class: a.result === "NO_DECISION" ? "res-nodec" : "res-win" }, resText),
        h("div", { class: "meta" }, "threshold " + a.threshold_hz + " Hz · candidate-relative score = mean(trial1 L−R, trial2 R−L) · match hash " + e.sha256));
      const wrap = h("div", { class: "trials" });
      box.append(wrap);
      for (const att of a.attempts) {
        wrap.append(h("div", { class: "meta", style: "margin-top:8px" }, "attempt " + att.attempt + " · variant " + att.variant + " · A_score " + (att.a_score ?? "—") + " · B_score " + (att.b_score ?? "—") + " · " + att.result));
        for (const [k, sha] of [["trial_1", att.trial_1_sha256], ["trial_2", att.trial_2_sha256]]) {
          const t = d.trials[sha]?.artifact;
          if (!t) continue;
          const maxHz = Math.max(parseFloat(t.left_hz), parseFloat(t.right_hz), 1);
          const bars = h("div", { class: "bars" },
            h("div", { class: "bar" }, h("span", null, "L"), h("div", { class: "track" }, h("div", { class: "fill", style: "width:" + (100 * parseFloat(t.left_hz) / maxHz) + "%" })), h("span", null, t.left_hz + " Hz")),
            h("div", { class: "bar right" }, h("span", null, "R"), h("div", { class: "track" }, h("div", { class: "fill", style: "width:" + (100 * parseFloat(t.right_hz) / maxHz) + "%" })), h("span", null, t.right_hz + " Hz")),
            h("div", { class: "meta" }, (k === "trial_1" ? "trial 1 (A left, B right)" : "trial 2 MIRRORED (B left, A right)") + " · gate spikes " + t.gate_spikes + " · raw " + t.result + " · neural window " + t.neural_window_ms + " ms"),
            h("div", { class: "meta" }, "left " + candidateLabel(m, t.category, t.left_candidate_id) + " · right " + candidateLabel(m, t.category, t.right_candidate_id)),
            h("div", { class: "meta" }, "input " + short(t.input_sha256) + " spikes " + short(t.spike_sha256) + " ckpt " + short(t.checkpoint_sha256))
          );
          const canvas = h("canvas", { class: "raster", title: "spike counts per readout cell (binned)" });
          bars.append(canvas);
          parseNpy("/run/" + t.spike_path).then((c) => drawRaster(canvas, c));
          wrap.append(h("div", { class: "trial" }, h("a", { href: "/run/" + t.frame_path, target: "_blank" }, h("img", { src: "/run/" + t.frame_path, alt: "trial input" })), bars));
        }
      }
    }
    // final + launch
    const fb = $("#final");
    if (d.final) {
      const f = d.final.artifact;
      const outcomeCls = f.outcome === "LAUNCH" ? "res-win" : "res-wait";
      fb.append(h("div", { class: outcomeCls, style: "font-size:20px" }, f.outcome + (f.reason ? " — " + f.reason : "")));
      const dl = h("dl", { class: "kv" });
      for (const cat of CATS) dl.append(h("dt", null, cat), h("dd", null, f.identity[cat] || f[cat] ? candidateLabel(m, cat, f.identity[cat] || f[cat]) + " (" + (f.identity[cat] || f[cat]) + ")" : h("span", { class: "res-nodec" }, "NO_DECISION / not selected")));
      dl.append(h("dt", null, "decision hash"), h("dd", { class: "hash" }, d.final.sha256));
      fb.append(dl);
      const ls = $("#launch");
      if (d.receipt && d.receipt.artifact.receipt) {
        const r = d.receipt.artifact.receipt;
        ls.append(h("div", null, h("span", { class: "sim" }, r.simulated ? "SIMULATED · " + r.network.toUpperCase() : r.network), " status ", d.receipt.artifact.status),
          h("dl", { class: "kv" }, h("dt", null, "mint"), h("dd", { class: "hash" }, r.mint), h("dt", null, "venue"), h("dd", null, r.venue + " (simulation mode)"), h("dt", null, "signature"), h("dd", { class: "hash" }, r.signature), h("dt", null, "receipt hash"), h("dd", { class: "hash" }, d.receipt.sha256)),
          h("a", { href: "/coin" }, "→ /coin"));
      } else if (d.veto) ls.append(h("div", { class: "warnbox" }, "LAUNCH VETOED: " + d.veto.artifact.veto));
      else if (d.intent) ls.append(h("div", { class: "warnbox" }, "Intent persisted, no receipt: " + (d.idx.stop || "unresolved")));
      else ls.append(h("div", { class: "res-wait" }, "No launch. " + (f.reason || "")));
    } else fb.append(h("div", { class: "meta" }, "final decision pending"));
    // default selection: last match
    if (d.matches.length) showMatch(d.matches[d.matches.length - 1]);
  }

  // ------------------------------------------------------------------ /coin
  async function coin() {
    const d = await load();
    headerBits(d);
    if (!d.run) return;
    const m = d.manifest;
    const f = d.final?.artifact;
    $("#disclosure").textContent = m.disclosure;
    const idBox = $("#identity");
    if (!f) { idBox.append(h("div", { class: "meta" }, "no final decision yet")); return; }
    const name = candidateLabel(m, "name", f.identity.name);
    const ticker = candidateLabel(m, "ticker", f.identity.ticker);
    idBox.append(h("div", { class: "big" }, name || h("span", { class: "res-nodec" }, "NO NAME"), " ", h("span", { class: "ticker" }, ticker ? "$" + ticker : "")));
    idBox.append(h("div", { class: "sub" }, candidateLabel(m, "description", f.identity.description) || "no description selected"));
    if (f.identity.logo && d.receipt) idBox.append(h("img", { class: "logo", src: "/run/final/logo.png", alt: "logo" }));
    const pal = m.categories.palette.find((p) => p.id === f.identity.palette);
    if (pal) idBox.append(h("div", { class: "swatches" }, pal.colors.map((c) => h("div", { class: "swatch", style: "background:" + c, title: c }))));
    const status = $("#status");
    status.append(h("div", { class: f.outcome === "LAUNCH" ? "res-win" : "res-wait", style: "font-size:18px" }, f.outcome + (f.reason ? " — " + f.reason : "")));
    const dl = h("dl", { class: "kv" });
    const add = (k, v, cls) => dl.append(h("dt", null, k), h("dd", { class: cls || "" }, v));
    add("selected from", "precommitted candidates only (manifest " + short(d.idx.manifest_sha256) + ")");
    add("venue", f.launch_venue ? f.launch_venue + " · simulation mode; no venue adapter is live" : "not selected");
    add("decision hash", d.final.sha256, "hash");
    if (d.receipt && d.receipt.artifact.receipt) {
      const r = d.receipt.artifact.receipt;
      add("network", h("span", { class: "sim" }, r.simulated ? "SIMULATED · " + r.network.toUpperCase() + " · NOT A REAL TOKEN" : r.network));
      add("mint", r.mint, "hash");
      add("transaction", r.signature, "hash");
      add("explorer", r.explorer_url ? h("a", { href: r.explorer_url }, r.explorer_url) : "none (mock)");
      add("mint authority", r.authorities.mint === null ? "revoked" : r.authorities.mint);
      add("freeze authority", r.authorities.freeze === null ? "revoked" : r.authorities.freeze);
      add("update authority", r.authorities.update === null ? "revoked" : r.authorities.update);
      add("creator allocation", r.creator_allocation_percent + " %");
      add("creator fee routing", r.creator_fee_disclosure);
      add("dev buy", d.intent.artifact.intent.initial_dev_buy_sol + " SOL");
      add("insider wallets", d.intent.artifact.intent.insider_wallets.length ? d.intent.artifact.intent.insider_wallets.join(", ") : "none");
      add("receipt hash", d.receipt.sha256, "hash");
    } else if (d.veto) add("launch", "VETOED: " + d.veto.artifact.veto, "res-nodec");
    else add("launch", "none");
    status.append(dl);
  }

  // ----------------------------------------------------------------- /brain
  async function brain() {
    const d = await load();
    headerBits(d);
    const b = await (await fetch("/api/brain")).json();
    const box = $("#brain");
    const dl = h("dl", { class: "kv" });
    const add = (k, v, cls) => dl.append(h("dt", null, k), h("dd", { class: cls || "" }, v));
    if (d.run) {
      add("backend in this run", d.run.backend === "fixture-brain-v1" ? h("span", { class: "sim" }, "FIXTURE BRAIN — deterministic stand-in, NOT a connectome") : "MaleCNS v1.0 retained graph");
      add("checkpoint", d.run.checkpoint_file + " · " + d.run.checkpoint_sha256, "hash");
      add("software commit", d.run.software.git_commit, "hash");
      add("package source hash", d.run.software.source_sha256, "hash");
      for (const side of ["left", "right", "gate"]) add("decoder cells · " + side, d.run.decoder_cells[side].join(", "));
    }
    add("baseline", h("a", { href: "https://github.com/nftechie/stonkfly" }, "nftechie/stonkfly") + "");
    add("baseline commit", b.baseline_commit, "hash");
    add("dataset", b.datasets.malecns_v1.release + " · " + b.datasets.malecns_v1.source);
    add("retained neurons", "166,700");
    add("directed edges", "25,582,938");
    add("synaptic contacts", "124,177,617");
    add("kernel", "C++17 event-driven LIF, 0.1 ms timestep");
    add("visual input", "3,335 R1–R6 luminance + 811 R8 colour inputs from a 320×180 RGB frame");
    add("readout", "DNp20 left/right mean rate, DNpe017 gate; mirrored candidate-relative score, threshold " + (d.manifest ? d.manifest.decoder_threshold_hz : "") + " Hz");
    for (const [name, info] of Object.entries(b.sources)) add(name, info.sha256 + " (" + info.bytes + " bytes)", "hash");
    box.append(dl);
    const lim = $("#limits");
    for (const t of [
      "Not consciousness. The network does not experience reward, pain or intention.",
      "Profitable learning has not been demonstrated. Identity selection runs with plasticity frozen and no reinforcement.",
      "The fly selected among authored candidates via an engineered decoder; it did not invent language or conceive a token.",
      "Sign proxies, LIF photoreceptors and the RGB display adapter are modeling assumptions, not validated fly physiology.",
      "A fixture backend run demonstrates the protocol and audit trail only; it says nothing about the connectome.",
    ]) lim.append(h("li", null, t));
  }

  const page = document.body.dataset.page;
  if (page === "live") return;
  ({ choose, coin, brain })[page]().catch((e) => { const w = $("#verify"); w.textContent = "ERROR " + e; w.className = "badge bad"; });
})();
