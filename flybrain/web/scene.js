/* Pixel-art replay of a hash-chained run: the fly at its desk, the monitor
   showing the exact trial frame, the wall panel lighting up from the stored
   spike counts, LEFT/RIGHT buttons pressed per the recorded readout. */
(function () {
  const canvas = document.getElementById("scene");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  const W = canvas.width, H = canvas.height;
  const $ = (s) => document.querySelector(s);

  // ------------------------------------------------------------ sprites
  const PAL = { k: "#0b0e14", g: "#4b5566", G: "#7a8699", h: "#9aa6b8", r: "#e11d48", R: "#ff7a95", w: "#b9d0f0", y: "#2a3040", a: "#bef264" };
  const FLY_A = [
    ".....wwwwwww....",
    "...wwwwwwwwwww..",
    "..www.......www.",
    "...GGGG.........",
    ".rRGGGGGgggg....",
    "rrrGGGGGgggggg..",
    ".rrGGGGGggkggkg.",
    "..GGGGGgggggggg.",
    "...ggggggggggg..",
    "....y..y..y.....",
    "...y...y...y....",
    "..y....y....y...",
  ];
  const FLY_B = [
    "................",
    "................",
    "...wwwwwwwwww...",
    "..wGGGGwwwwwwww.",
    ".rRGGGGGgggg.ww.",
    "rrrGGGGGgggggg..",
    ".rrGGGGGggkggkg.",
    "..GGGGGgggggggg.",
    "...ggggggggggg..",
    "....y..y..y.....",
    "....y..y..y.....",
    "...y...y...y....",
  ];
  function drawSprite(rows, x, y, s, flip) {
    ctx.save();
    ctx.translate(x, y);
    if (flip) { ctx.scale(-1, 1); ctx.translate(-rows[0].length * s, 0); }
    for (let r = 0; r < rows.length; r++) for (let c = 0; c < rows[r].length; c++) {
      const ch = rows[r][c];
      if (ch === ".") continue;
      ctx.fillStyle = PAL[ch] || ch;
      if (ch === "w") ctx.globalAlpha = 0.65;
      ctx.fillRect(c * s, r * s, s, s);
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }
  function px(x, y, w, h, color) { ctx.fillStyle = color; ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h)); }
  function text(t, x, y, color, size, align) {
    ctx.font = `${size || 10}px ui-monospace, Menlo, monospace`;
    ctx.fillStyle = color; ctx.textAlign = align || "left"; ctx.textBaseline = "top";
    ctx.fillText(t, x, y);
  }

  // ------------------------------------------------------------ state
  const S = {
    events: [], i: 0, playing: false, speed: 1,
    fly: { x: 300, y: 262, target: 300, facing: 1, mode: "idle", t: 0, hop: 0 },
    bubble: null, bubbleUntil: 0,
    frameImg: null, spikes: null, readout: null,
    pressed: null, pressUntil: 0,
    banner: null, bannerUntil: 0,
    coin: null, launch: null, confetti: [],
    tape: "", clock: 0, manifest: null, run: null,
  };
  const now = () => performance.now();

  function say(t, ms) { S.bubble = t; S.bubbleUntil = now() + ms / S.speed; }
  function banner(t, color, ms) { S.banner = { t, color }; S.bannerUntil = now() + ms / S.speed; }
  function candidateLabel(cat, id) {
    if (!id || !S.manifest) return id || "";
    const c = (S.manifest.categories[cat] || []).find((x) => x.id === id);
    return c ? (c.text || c.label || id) : id;
  }
  async function parseNpy(url) {
    const buf = await (await fetch(url)).arrayBuffer();
    const v = new DataView(buf);
    const major = v.getUint8(6);
    const hl = major === 1 ? v.getUint16(8, true) : v.getUint32(8, true);
    return new Int32Array(buf.slice((major === 1 ? 10 : 12) + hl));
  }
  function loadImage(url) { return new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; }); }

  // ------------------------------------------------------------ events
  function buildEvents(chain) {
    const ev = [];
    for (const e of chain) {
      const a = e.artifact;
      if (e.kind === "trial") ev.push({ type: "trial", a, sha: e.sha256 });
      else if (e.kind === "match_result") ev.push({ type: "match", a, sha: e.sha256 });
      else if (e.kind === "category_result") ev.push({ type: "category", a, sha: e.sha256 });
      else if (e.kind === "final_decision") ev.push({ type: "final", a, sha: e.sha256 });
      else if (e.kind === "launch_receipt") ev.push({ type: "launch", a, sha: e.sha256 });
      else if (e.kind === "launch_veto") ev.push({ type: "veto", a, sha: e.sha256 });
    }
    return ev;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms / S.speed));
  let running = false;
  async function runEvent(ev) {
    const a = ev.a;
    if (ev.type === "trial") {
      S.tape = `chain #${a.chain_seq} · trial ${a.category} r${a.round} m${a.match} a${a.attempt} t${a.trial} (${a.variant}) · left ${candidateLabel(a.category, a.left_candidate_id)} · right ${candidateLabel(a.category, a.right_candidate_id)} · input ${a.input_sha256.slice(0, 12)}… spikes ${a.spike_sha256.slice(0, 12)}…`;
      S.readout = null; S.spikes = null; S.pressed = null;
      S.fly.target = 300; S.fly.mode = "idle";
      const [img, spikes] = await Promise.all([loadImage("/run/" + a.frame_path), parseNpy("/run/" + a.spike_path)]);
      S.frameImg = img;
      say(a.trial === 2 ? "MIRRORED…" : "HMM…", 900);
      await sleep(500);
      S.spikes = spikes; S.spikeT = now();
      await sleep(900);
      S.readout = a;
      const side = a.result;
      if (side === "LEFT" || side === "RIGHT") {
        S.fly.target = side === "LEFT" ? 170 : 470;
        S.fly.mode = "walk";
        say(side + "!", 1400);
        await sleep(800);
        S.fly.mode = "press"; S.pressed = side; S.pressUntil = now() + 500 / S.speed;
        await sleep(450);
        S.fly.mode = "idle";
      } else {
        say(side === "NO_GATE" ? "…no gate spike" : "…tie", 1400);
        await sleep(900);
      }
      await sleep(300);
    } else if (ev.type === "match") {
      const res = a.result === "NO_DECISION" ? "NO_DECISION — nobody picks" : `${a.category.replace("_", " ")}: ${candidateLabel(a.category, a.result)}`;
      banner(res, a.result === "NO_DECISION" ? "#fb7185" : a.result === "wait" ? "#fbbf24" : "#bef264", 1800);
      S.tape = `chain #${a.chain_seq} · match ${a.category} r${a.round} m${a.match} · ${a.attempts.length}/${a.max_attempts} attempts · A_score ${a.attempts[a.attempts.length - 1].a_score ?? "—"} · ${ev.sha.slice(0, 12)}…`;
      S.fly.target = 300; S.fly.mode = a.result === "NO_DECISION" ? "shrug" : "idle";
      say(a.result === "NO_DECISION" ? "¯\\_(ツ)_/¯" : a.result === "wait" ? "not yet." : "ok.", 1500);
      await sleep(1800);
    } else if (ev.type === "category") {
      const w = a.category === "launch_action" ? a.result : (a.winner ? candidateLabel(a.category, a.winner) : "NO_DECISION");
      banner(`${a.category.replace("_", " ").toUpperCase()} → ${w}`, a.winner || a.result === "LAUNCH" ? "#38bdf8" : "#fb7185", 1600);
      S.tape = `chain #${a.chain_seq} · category root ${a.category} ${ev.sha.slice(0, 16)}… committed as memo payload`;
      await sleep(1600);
    } else if (ev.type === "final") {
      S.coin = a;
      S.tape = `chain #${a.chain_seq} · final decision ${ev.sha.slice(0, 16)}… · ${a.outcome}${a.reason ? " · " + a.reason : ""}`;
      if (a.outcome === "LAUNCH") { S.fly.mode = "party"; say("LAUNCH!!!", 4000); for (let k = 0; k < 120; k++) S.confetti.push({ x: Math.random() * W, y: -Math.random() * 200, v: 1 + Math.random() * 2, c: ["#bef264", "#38bdf8", "#fb7185", "#fbbf24"][k % 4] }); }
      else { S.fly.mode = "shrug"; say("no token. the fly said no.", 4000); }
      await sleep(2500);
    } else if (ev.type === "launch") {
      S.launch = a;
      S.tape = `chain #${a.chain_seq} · launch receipt ${ev.sha.slice(0, 16)}… · ${a.status} · mint ${a.receipt ? a.receipt.mint : "—"} · ${a.receipt && a.receipt.simulated ? "SIMULATED" : ""}`;
      await sleep(2500);
    } else if (ev.type === "veto") {
      banner("LAUNCH VETOED: " + a.veto, "#fb7185", 3000);
      S.fly.mode = "shrug";
      await sleep(3000);
    }
  }
  async function play() {
    if (running) return;
    running = true;
    while (S.playing && S.i < S.events.length) {
      $("#progress").textContent = `event ${S.i + 1}/${S.events.length}`;
      await runEvent(S.events[S.i]);
      S.i++;
    }
    if (S.i >= S.events.length) { S.playing = false; $("#play").textContent = "↺ replay"; $("#progress").textContent = `done · ${S.events.length} events`; }
    running = false;
  }
  function skipToEnd() {
    S.playing = false;
    S.i = S.events.length;
    const fin = S.events.find((e) => e.type === "final");
    const la = S.events.find((e) => e.type === "launch");
    const last = [...S.events].reverse().find((e) => e.type === "trial");
    if (last) { loadImage("/run/" + last.a.frame_path).then((im) => (S.frameImg = im)); parseNpy("/run/" + last.a.spike_path).then((s) => { S.spikes = s; S.spikeT = now(); }); S.readout = last.a; }
    if (fin) { S.coin = fin.a; S.fly.mode = fin.a.outcome === "LAUNCH" ? "party" : "shrug"; }
    if (la) S.launch = la.a;
    $("#progress").textContent = `done · ${S.events.length} events`;
    $("#play").textContent = "↺ replay";
  }

  // ------------------------------------------------------------ drawing
  function drawRoom() {
    px(0, 0, W, H, "#070a12");
    for (let y = 0; y < 200; y += 16) for (let x = 0; x < W; x += 16) px(x, y, 15, 15, (x / 16 + y / 16) % 2 ? "#0a0e19" : "#090d17");
    px(0, 272, W, 60, "#0b0f1a");
    // desk (deep top surface; monitor at the back, fly and buttons at the front)
    px(40, 200, 560, 68, "#232b3e"); px(40, 200, 560, 4, "#334061"); px(40, 268, 560, 5, "#141a28");
    px(60, 273, 14, 50, "#141a28"); px(566, 273, 14, 50, "#141a28");
    // monitor
    px(200, 40, 240, 150, "#1a2030"); px(206, 46, 228, 136, "#05070c");
    px(300, 190, 40, 7, "#1a2030"); px(278, 197, 84, 3, "#2a3247");
    if (S.coin) drawCoinOnScreen();
    else if (S.frameImg) { ctx.imageSmoothingEnabled = false; ctx.drawImage(S.frameImg, 208, 51, 224, 126); }
    else text("NO SIGNAL", 320, 108, "#3b4b6e", 10, "center");
    // buttons
    for (const [side, x] of [["LEFT", 118], ["RIGHT", 522]]) {
      const down = S.pressed === side && now() < S.pressUntil;
      px(x - 28, 214 + (down ? 4 : 0), 56, 22 - (down ? 4 : 0), side === "LEFT" ? "#1d4ed8" : "#be123c");
      px(x - 28, 232, 56, 6, "#111827");
      px(x - 24, 217 + (down ? 4 : 0), 48, 4, "rgba(255,255,255,0.18)");
      text(side, x, 242, "#9aa6b8", 9, "center");
    }
    // wall panel: neurons
    px(450, 20, 176, 84, "#0b1120"); px(450, 20, 176, 2, "#1f2a44"); px(450, 102, 176, 2, "#1f2a44");
    text("READOUT CELLS · spike counts", 458, 25, "#7d8bab", 8);
    const sp = S.spikes;
    const cols = 32, rows = 8, cw = 4.5, chh = 6;
    let maxc = 1;
    const bins = new Float32Array(cols * rows);
    if (sp) { for (let k = 0; k < sp.length; k++) bins[Math.floor((k * cols * rows) / sp.length)] += sp[k]; for (const b of bins) maxc = Math.max(maxc, b); }
    const age = sp ? Math.min(1, (now() - S.spikeT) / 700) : 0;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const v = sp ? (bins[r * cols + c] / maxc) * age : 0;
      const flick = sp && Math.random() < v * 0.15 ? 1 : 0;
      px(458 + c * (cw + 0.5), 36 + r * (chh + 1), cw, chh, v > 0.66 || flick ? "#bef264" : v > 0.33 ? "#38bdf8" : v > 0 ? "#243a5e" : "#111a2c");
    }
    // rates
    px(14, 20, 176, 84, "#0b1120"); px(14, 20, 176, 2, "#1f2a44"); px(14, 102, 176, 2, "#1f2a44");
    text("DNp20 L / R · DNpe017 GATE", 20, 25, "#7d8bab", 8);
    const ro = S.readout;
    const L = ro ? parseFloat(ro.left_hz) : 0, R = ro ? parseFloat(ro.right_hz) : 0, mx = Math.max(L, R, 1);
    px(20, 40, 116, 10, "#111a2c"); px(20, 40, 116 * (L / mx), 10, "#38bdf8"); text(ro ? L.toFixed(2) + " Hz" : "—", 140, 41, "#dbe5f9", 8);
    px(20, 56, 116, 10, "#111a2c"); px(20, 56, 116 * (R / mx), 10, "#fb7185"); text(ro ? R.toFixed(2) + " Hz" : "—", 140, 57, "#dbe5f9", 8);
    const gate = ro ? ro.gate_spikes : 0;
    px(20, 74, 10, 10, gate ? "#bef264" : "#3b1d1d"); text(ro ? `gate ${gate} spike${gate === 1 ? "" : "s"}` : "gate —", 36, 75, "#dbe5f9", 8);
    text(ro ? `ckpt ${ro.checkpoint_sha256.slice(0, 8)}… ${ro.neural_window_ms} ms · ${ro.backend}` : "", 20, 90, "#7d8bab", 6);
  }
  function drawCoinOnScreen() {
    const a = S.coin, m = S.manifest;
    const x = 206, y = 46, w = 228, h = 136;
    px(x, y, w, h, "#0b1120"); px(x, y, w, 3, a.outcome === "LAUNCH" ? "#bef264" : "#fb7185");
    const name = candidateLabel("name", a.identity.name) || "NO NAME", tick = candidateLabel("ticker", a.identity.ticker);
    text(name, x + 10, y + 12, "#f8fafc", 16); text(tick ? "$" + tick : "", x + 10, y + 32, "#bef264", 13);
    const logo = m && a.identity.logo ? m.categories.logo.find((l) => l.id === a.identity.logo) : null;
    if (logo) { px(x + 160, y + 10, 56, 56, logo.bg); logo.pixels.forEach((row, r) => [...row].forEach((ch, c) => { if (ch === "#") px(x + 164 + c * 6, y + 14 + r * 6, 6, 6, logo.fg); })); }
    const pal = m && a.identity.palette ? m.categories.palette.find((p) => p.id === a.identity.palette) : null;
    if (pal) pal.colors.forEach((c, k) => px(x + 10 + k * 30, y + 52, 28, 10, c));
    const desc = candidateLabel("description", a.identity.description);
    if (desc) text(desc.slice(0, 40) + (desc.length > 40 ? "…" : ""), x + 10, y + 68, "#9aa6b8", 7);
    text(a.outcome === "LAUNCH" ? "LAUNCH" : "NO LAUNCH", x + 10, y + 84, a.outcome === "LAUNCH" ? "#bef264" : "#fb7185", 12);
    if (a.reason) text(a.reason.slice(0, 44), x + 10, y + 100, "#fb7185", 7);
    if (S.launch && S.launch.receipt) {
      const r = S.launch.receipt;
      text((r.simulated ? "SIMULATED · " : "") + r.network.toUpperCase() + " · venue " + r.venue, x + 10, y + 100, "#fbbf24", 8);
      text("mint " + r.mint.slice(0, 26) + "…", x + 10, y + 112, "#38bdf8", 7);
      text("not a real token · selected from precommitted candidates", x + 10, y + 123, "#7d8bab", 6);
    } else if (a.outcome === "LAUNCH") text("launch pending…", x + 10, y + 100, "#7d8bab", 8);
    else text("selected from precommitted candidates · nobody overrides", x + 10, y + 116, "#7d8bab", 6);
  }
  function drawFly(t) {
    const f = S.fly;
    const dx = f.target - f.x;
    if (Math.abs(dx) > 2) { f.x += Math.sign(dx) * Math.min(Math.abs(dx), 4 * S.speed); f.facing = Math.sign(dx); }
    let bob = 0;
    if (f.mode === "walk") bob = Math.sin(t / 60) * 2;
    if (f.mode === "party") bob = -Math.abs(Math.sin(t / 120)) * 18;
    if (f.mode === "press") bob = 4;
    if (f.mode === "shrug") bob = Math.sin(t / 300) * 1;
    const wings = Math.floor(t / 90) % 2 === 0 || f.mode === "idle" && Math.floor(t / 400) % 3 === 0;
    drawSprite(wings ? FLY_A : FLY_B, f.x - 40, f.y - 60 + bob, 5, f.facing < 0);
    if (f.mode === "party") { text("♪", f.x + 48, f.y - 80 + bob, "#bef264", 14); text("♪", f.x - 58, f.y - 70 - bob, "#38bdf8", 12); }
    if (S.bubble && now() < S.bubbleUntil) {
      const w = Math.max(60, S.bubble.length * 7 + 16);
      px(f.x - w / 2, f.y - 96 + bob, w, 22, "#f8fafc"); px(f.x - 4, f.y - 74 + bob, 8, 6, "#f8fafc");
      text(S.bubble, f.x, f.y - 91 + bob, "#0b0e14", 10, "center");
    }
  }
  function drawOverlay(t) {
    if (S.banner && now() < S.bannerUntil) {
      px(0, 284, W, 26, "rgba(5,7,12,0.85)"); px(0, 284, W, 2, S.banner.color);
      text(S.banner.t, W / 2, 291, S.banner.color, 12, "center");
    }
    for (const c of S.confetti) { c.y += c.v * S.speed; if (c.y > H) c.y = -10; px(c.x, c.y, 3, 5, c.c); }
    $("#tape").innerHTML = S.tape ? S.tape.replace(/([0-9a-f]{12,}…?)/g, "<span>$1</span>") : "…";
  }
  function loop(t) { drawRoom(); drawFly(t); drawOverlay(t); requestAnimationFrame(loop); }

  // ------------------------------------------------------------ boot
  async function boot() {
    const idx = await (await fetch("/api/index")).json();
    S.manifest = idx.manifest;
    S.events = buildEvents(idx.chain);
    const run = idx.chain.find((e) => e.kind === "run_header");
    S.run = run ? run.artifact : null;
    if (S.manifest) $("#disclosure").textContent = S.manifest.disclosure;
    $("#run-id").textContent = S.run ? S.run.run_id : "no run";
    const b = $("#backend"); b.textContent = S.run ? S.run.backend : ""; b.className = "badge " + (S.run && S.run.backend === "fixture-brain-v1" ? "warn" : "ok");
    fetch("/api/verify").then((r) => r.json()).then((rep) => { const w = $("#verify"); w.textContent = (rep.ok ? "VERIFIED " : "VERIFY FAILED ") + rep.checks.length + " checks"; w.className = "badge " + (rep.ok ? "ok" : "bad"); });
    S.tape = `run ${S.run ? S.run.run_id : "?"} · manifest ${idx.manifest_sha256 ? idx.manifest_sha256.slice(0, 16) + "…" : "—"} · ${S.events.length} events on the chain · press play`;
    $("#progress").textContent = `${S.events.length} events`;
    $("#play").onclick = () => {
      if (S.i >= S.events.length) { S.i = 0; S.coin = null; S.launch = null; S.confetti = []; S.fly.mode = "idle"; S.frameImg = null; S.spikes = null; S.readout = null; }
      S.playing = !S.playing; $("#play").textContent = S.playing ? "⏸ pause" : "▶ play"; if (S.playing) play();
    };
    $("#step").onclick = async () => { if (running || S.i >= S.events.length) return; S.playing = false; $("#play").textContent = "▶ play"; running = true; await runEvent(S.events[S.i]); S.i++; running = false; $("#progress").textContent = `event ${S.i}/${S.events.length}`; };
    $("#end").onclick = skipToEnd;
    $("#speed").onchange = (e) => (S.speed = parseFloat(e.target.value));
    requestAnimationFrame(loop);
    S.playing = true; $("#play").textContent = "⏸ pause"; play();
  }
  boot().catch((e) => { $("#tape").textContent = "ERROR " + e; });
})();
