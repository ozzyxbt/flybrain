/* three.js replay of a hash-chained run.
   Desk, monitor (the exact trial frame as a texture), LEFT/RIGHT buttons, a
   smooth fly; and beside it fixed frontal/dorsal CNS projections where every
   positioned soma is a dim point and the cells that fired in the current
   trial light up from the recorded spike counts. */
(function () {
  const stage = document.getElementById("stage3d");
  if (!stage) return;
  const $ = (s) => document.querySelector(s);
  if (!window.THREE || !window.FLYLIB) { $("#tape").textContent = "three.js / flylib failed to load"; return; }
  const T = window.THREE;

  // ------------------------------------------------------------ renderer
  const L = window.FLYLIB;
  const { renderer, scene, camera } = L.createStage(stage);
  camera.position.set(0, 2.35, 4.9);
  camera.lookAt(0, 1.35, -0.3);
  const label = L.label;

  // --------------------------------------------------------------- room
  const M = (o) => new T.MeshStandardMaterial(o);
  const floor = new T.Mesh(new T.PlaneGeometry(16, 10), M({ color: 0x0b0f1a, roughness: 0.95 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const wall = new T.Mesh(new T.PlaneGeometry(16, 8), M({ color: 0x0a0e19, roughness: 1 }));
  wall.position.set(0, 4, -1.6); wall.receiveShadow = true; scene.add(wall);
  const grid = new T.GridHelper(16, 32, 0x1a2338, 0x121a2c); grid.position.set(0, 0.6, -1.59); grid.rotation.x = Math.PI / 2; scene.add(grid);
  const desk = new T.Mesh(new T.BoxGeometry(5.4, 0.12, 1.9), M({ color: 0x2a3247, roughness: 0.6, metalness: 0.05 }));
  desk.position.set(0, 0.84, 0); desk.castShadow = true; desk.receiveShadow = true; scene.add(desk);
  for (const x of [-2.4, 2.4]) { const leg = new T.Mesh(new T.BoxGeometry(0.16, 0.8, 1.6), M({ color: 0x141a28 })); leg.position.set(x, 0.4, 0); scene.add(leg); }
  // monitor
  const frame = new T.Mesh(new T.BoxGeometry(2.42, 1.44, 0.08), M({ color: 0x1a2030, roughness: 0.5 }));
  frame.position.set(0, 1.78, -0.6); frame.castShadow = true; scene.add(frame);
  const screenMat = new T.MeshBasicMaterial({ color: 0x05070c });
  const screen = new T.Mesh(new T.PlaneGeometry(2.24, 1.26), screenMat);
  screen.position.set(0, 1.78, -0.555); scene.add(screen);
  const stand = new T.Mesh(new T.CylinderGeometry(0.06, 0.1, 0.5, 12), M({ color: 0x1a2030 })); stand.position.set(0, 1.05, -0.6); scene.add(stand);
  const base = new T.Mesh(new T.CylinderGeometry(0.35, 0.4, 0.04, 24), M({ color: 0x1f2a44 })); base.position.set(0, 0.92, -0.6); scene.add(base);
  // buttons
  const buttons = {};
  for (const [side, x, color] of [["LEFT", -1.75, 0x1d4ed8], ["RIGHT", 1.75, 0xbe123c]]) {
    const g = new T.Group(); g.position.set(x, 0.9, 0.35);
    const ring = new T.Mesh(new T.CylinderGeometry(0.3, 0.32, 0.06, 32), M({ color: 0x111827, roughness: 0.4 })); ring.position.y = 0.03; ring.castShadow = true; g.add(ring);
    const cap = new T.Mesh(new T.CylinderGeometry(0.24, 0.25, 0.12, 32), M({ color, roughness: 0.35, emissive: color, emissiveIntensity: 0.15 })); cap.position.y = 0.12; cap.castShadow = true; g.add(cap);
    g.add(label(side, 0.9, 0.11, "#dbe5f9", 0, 0.02, 0.5));
    scene.add(g); buttons[side] = { g, cap, color };
  }

  // ---------------------------------------------------------------- fly
  const flyRig = L.buildFly(scene);
  const fly = flyRig.group;
  const animateFly = flyRig.animate;
  const { CNS, loadAtlas, animateCNS } = L;
  const setActivity = L.setActivity;

  // -------------------------------------------------------------- state
  const S = { events: [], i: 0, playing: false, speed: 1, fly: { x: 0, target: 0, yaw: Math.PI / 2, targetYaw: Math.PI / 2, mode: "idle" }, readout: null, pressed: null, pressUntil: 0, coin: null, launch: null, manifest: null, run: null, confetti: [], tape: "" };
  const now = () => performance.now();
  function say(t, ms) { const b = $("#bubble"); b.textContent = t; b.style.display = "block"; clearTimeout(say.timer); say.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  function banner(t, color, ms) { const b = $("#banner"); b.textContent = t; b.style.borderTopColor = color; b.style.color = color; b.style.display = "block"; clearTimeout(banner.timer); banner.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  function candidateLabel(cat, id) { if (!id || !S.manifest) return id || ""; const c = (S.manifest.categories[cat] || []).find((x) => x.id === id); return c ? (c.text || c.label || id) : id; }
  async function parseNpy(url) { const buf = await (await fetch(url)).arrayBuffer(); const v = new DataView(buf); const major = v.getUint8(6); const hl = major === 1 ? v.getUint16(8, true) : v.getUint32(8, true); return new Int32Array(buf.slice((major === 1 ? 10 : 12) + hl)); }
  const texLoader = new T.TextureLoader();
  function showFrame(url) {
    texLoader.load(url, (tex) => { tex.magFilter = T.NearestFilter; tex.minFilter = T.LinearFilter; tex.colorSpace = T.SRGBColorSpace; screenMat.map = tex; screenMat.color.set(0xffffff); screenMat.needsUpdate = true; });
  }
  function showCoin(a) {
    const m = S.manifest, c = document.createElement("canvas"); c.width = 448; c.height = 252; const x = c.getContext("2d");
    x.fillStyle = "#0b1120"; x.fillRect(0, 0, 448, 252); x.fillStyle = a.outcome === "LAUNCH" ? "#bef264" : "#fb7185"; x.fillRect(0, 0, 448, 6);
    x.font = "bold 34px ui-monospace, Menlo, monospace"; x.fillStyle = "#f8fafc"; x.textBaseline = "top"; x.fillText(candidateLabel("name", a.identity.name) || "NO NAME", 20, 22);
    const tick = candidateLabel("ticker", a.identity.ticker); x.font = "bold 26px ui-monospace, Menlo, monospace"; x.fillStyle = "#bef264"; x.fillText(tick ? "$" + tick : "", 20, 64);
    const logo = m && a.identity.logo ? m.categories.logo.find((l) => l.id === a.identity.logo) : null;
    if (logo) { x.fillStyle = logo.bg; x.fillRect(320, 20, 104, 104); x.fillStyle = logo.fg; logo.pixels.forEach((row, r) => [...row].forEach((ch, k) => { if (ch === "#") x.fillRect(324 + k * 12, 24 + r * 12, 12, 12); })); }
    const pal = m && a.identity.palette ? m.categories.palette.find((p) => p.id === a.identity.palette) : null;
    if (pal) pal.colors.forEach((col, k) => { x.fillStyle = col; x.fillRect(20 + k * 58, 104, 54, 18); });
    x.font = "13px ui-monospace, Menlo, monospace"; x.fillStyle = "#9aa6b8"; const d = candidateLabel("description", a.identity.description) || ""; x.fillText(d.slice(0, 44), 20, 134); if (d.length > 44) x.fillText(d.slice(44, 88), 20, 150);
    x.font = "bold 22px ui-monospace, Menlo, monospace"; x.fillStyle = a.outcome === "LAUNCH" ? "#bef264" : "#fb7185"; x.fillText(a.outcome === "LAUNCH" ? "LAUNCH" : "NO LAUNCH", 20, 172);
    x.font = "13px ui-monospace, Menlo, monospace";
    if (S.launch && S.launch.receipt) { const r = S.launch.receipt; x.fillStyle = "#fbbf24"; x.fillText((r.simulated ? "SIMULATED · " : "") + r.network.toUpperCase() + " · venue " + r.venue, 20, 202); x.fillStyle = "#38bdf8"; x.fillText("mint " + r.mint, 20, 220); x.fillStyle = "#7d8bab"; x.fillText("not a real token · selected from precommitted candidates", 20, 236); }
    else if (a.reason) { x.fillStyle = "#fb7185"; x.fillText(a.reason.slice(0, 50), 20, 202); x.fillStyle = "#7d8bab"; x.fillText("nobody overrides the fly", 20, 220); }
    const tex = new T.CanvasTexture(c); tex.colorSpace = T.SRGBColorSpace; screenMat.map = tex; screenMat.color.set(0xffffff); screenMat.needsUpdate = true;
  }
  function showReadout(a) {
    S.readout = a;
    const L = a ? parseFloat(a.left_hz) : 0, R = a ? parseFloat(a.right_hz) : 0, mx = Math.max(L, R, 1);
    $("#bar-l").style.width = a ? (100 * L / mx) + "%" : "0"; $("#bar-r").style.width = a ? (100 * R / mx) + "%" : "0";
    $("#hz-l").textContent = a ? L.toFixed(2) + " Hz" : "—"; $("#hz-r").textContent = a ? R.toFixed(2) + " Hz" : "—";
    const g = a ? a.gate_spikes : 0; $("#gate-led").className = "gate" + (g ? " on" : ""); $("#gate-txt").textContent = a ? `gate ${g} spike${g === 1 ? "" : "s"} · raw ${a.result}` : "gate —";
    $("#hud-ckpt").textContent = a ? `ckpt ${a.checkpoint_sha256.slice(0, 10)}… · ${a.neural_window_ms} ms · ${a.backend}` : "";
    const cr = $("#cns-rates"); if (cr) cr.textContent = a ? `DNp20 L ${L.toFixed(1)} Hz · R ${R.toFixed(1)} Hz · gate ${g}` : "DNp20 L — · R — · gate —";
  }

  // ------------------------------------------------------------- events
  function buildEvents(chain) {
    const ev = [];
    for (const e of chain) {
      const a = e.artifact, k = e.kind;
      if (k === "trial") ev.push({ type: "trial", a, sha: e.sha256 });
      else if (k === "match_result") ev.push({ type: "match", a, sha: e.sha256 });
      else if (k === "category_result") ev.push({ type: "category", a, sha: e.sha256 });
      else if (k === "final_decision") ev.push({ type: "final", a, sha: e.sha256 });
      else if (k === "launch_receipt") ev.push({ type: "launch", a, sha: e.sha256 });
      else if (k === "launch_veto") ev.push({ type: "veto", a, sha: e.sha256 });
    }
    return ev;
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms / S.speed));
  let running = false;
  async function runEvent(ev) {
    const a = ev.a;
    if (ev.type === "trial") {
      S.tape = `chain #${a.chain_seq} · trial ${a.category} r${a.round} m${a.match} a${a.attempt} t${a.trial} (${a.variant}) · left ${candidateLabel(a.category, a.left_candidate_id)} · right ${candidateLabel(a.category, a.right_candidate_id)} · input ${a.input_sha256.slice(0, 12)}… spikes ${a.spike_sha256.slice(0, 12)}…`;
      showReadout(null); setActivity(null); S.pressed = null; S.fly.target = 0; S.fly.mode = "idle";
      showFrame("/run/" + a.frame_path);
      const spikes = await parseNpy("/run/" + a.spike_path);
      say(a.trial === 2 ? "MIRRORED…" : "HMM…", 900);
      await sleep(500);
      setActivity(spikes);
      await sleep(1000);
      showReadout(a);
      const side = a.result;
      if (side === "LEFT" || side === "RIGHT") {
        S.fly.target = side === "LEFT" ? -1.35 : 1.35; S.fly.mode = "walk"; say(side + "!", 1500);
        await sleep(900);
        S.fly.mode = "press"; S.pressed = side; S.pressUntil = now() + 500 / S.speed;
        await sleep(500);
        S.fly.mode = "idle";
      } else { say(side === "NO_GATE" ? "…no gate spike" : "…tie", 1400); await sleep(900); }
      await sleep(300);
    } else if (ev.type === "match") {
      const res = a.result === "NO_DECISION" ? "NO_DECISION — nobody picks" : `${a.category.replace("_", " ")}: ${candidateLabel(a.category, a.result)}`;
      banner(res, a.result === "NO_DECISION" ? "#fb7185" : a.result === "wait" ? "#fbbf24" : "#bef264", 1800);
      S.tape = `chain #${a.chain_seq} · match ${a.category} r${a.round} m${a.match} · ${a.attempts.length}/${a.max_attempts} attempts · A_score ${a.attempts[a.attempts.length - 1].a_score ?? "—"} · ${ev.sha.slice(0, 12)}…`;
      S.fly.target = 0; S.fly.mode = a.result === "NO_DECISION" ? "shrug" : "idle";
      say(a.result === "NO_DECISION" ? "¯\\_(ツ)_/¯" : a.result === "wait" ? "not yet." : "ok.", 1500);
      await sleep(1800);
    } else if (ev.type === "category") {
      const w = a.category === "launch_action" ? a.result : (a.winner ? candidateLabel(a.category, a.winner) : "NO_DECISION");
      banner(`${a.category.replace("_", " ").toUpperCase()} → ${w}`, a.winner || a.result === "LAUNCH" ? "#38bdf8" : "#fb7185", 1600);
      S.tape = `chain #${a.chain_seq} · category root ${a.category} ${ev.sha.slice(0, 16)}… committed as memo payload`;
      await sleep(1600);
    } else if (ev.type === "final") {
      S.coin = a; showCoin(a);
      S.tape = `chain #${a.chain_seq} · final decision ${ev.sha.slice(0, 16)}… · ${a.outcome}${a.reason ? " · " + a.reason : ""}`;
      if (a.outcome === "LAUNCH") { S.fly.mode = "party"; say("LAUNCH!!!", 4000); spawnConfetti(); } else { S.fly.mode = "shrug"; say("no token. the fly said no.", 4000); }
      await sleep(2500);
    } else if (ev.type === "launch") {
      S.launch = a; if (S.coin) showCoin(S.coin);
      S.tape = `chain #${a.chain_seq} · launch receipt ${ev.sha.slice(0, 16)}… · ${a.status} · mint ${a.receipt ? a.receipt.mint : "—"} · ${a.receipt && a.receipt.simulated ? "SIMULATED" : ""}`;
      await sleep(2500);
    } else if (ev.type === "veto") { banner("LAUNCH VETOED: " + a.veto, "#fb7185", 3000); S.fly.mode = "shrug"; await sleep(3000); }
  }
  async function play() {
    if (running) return; running = true;
    while (S.playing && S.i < S.events.length) { $("#progress").textContent = `event ${S.i + 1}/${S.events.length}`; await runEvent(S.events[S.i]); S.i++; }
    if (S.i >= S.events.length) { S.playing = false; $("#play").textContent = "↺ replay"; $("#progress").textContent = `done · ${S.events.length} events`; }
    running = false;
  }
  function skipToEnd() {
    S.playing = false; S.i = S.events.length;
    const fin = S.events.find((e) => e.type === "final"), la = S.events.find((e) => e.type === "launch"), last = [...S.events].reverse().find((e) => e.type === "trial");
    if (last) { parseNpy("/run/" + last.a.spike_path).then(setActivity); showReadout(last.a); }
    if (la) S.launch = la.a;
    if (fin) { S.coin = fin.a; showCoin(fin.a); S.fly.mode = fin.a.outcome === "LAUNCH" ? "party" : "shrug"; if (fin.a.outcome === "LAUNCH") spawnConfetti(); }
    $("#progress").textContent = `done · ${S.events.length} events`; $("#play").textContent = "↺ replay";
  }
  // confetti (instanced boxes)
  const confettiGeo = new T.BoxGeometry(0.04, 0.06, 0.01), confettiMat = new T.MeshBasicMaterial({ vertexColors: false });
  function spawnConfetti() {
    for (let k = 0; k < 140; k++) {
      const m = new T.Mesh(confettiGeo, new T.MeshBasicMaterial({ color: [0xbef264, 0x38bdf8, 0xfb7185, 0xfbbf24][k % 4] }));
      m.position.set((Math.random() - 0.5) * 6, 3.5 + Math.random() * 2, (Math.random() - 0.5) * 2); m.userData.v = 0.01 + Math.random() * 0.02; m.userData.r = Math.random() * 0.2;
      scene.add(m); S.confetti.push(m);
    }
  }

  // --------------------------------------------------------------- loop
  let last = now();
  const headPos = new T.Vector3();
  function loop(t) {
    const dt = Math.min(50, t - last); last = t;
    const f = S.fly, dx = f.target - f.x, moving = Math.abs(dx) > 0.02;
    if (moving) f.x += Math.sign(dx) * Math.min(Math.abs(dx), 0.028 * S.speed * dt / 16);
    if (moving) f.targetYaw = dx > 0 ? 0 : Math.PI; else if (f.mode === "party") f.targetYaw = f.yaw + 0.1 * S.speed; else f.targetYaw = Math.PI / 2;
    let dyaw = ((f.targetYaw - f.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    f.yaw += Math.abs(dyaw) < 0.02 ? dyaw : Math.sign(dyaw) * Math.min(Math.abs(dyaw), 0.16 * S.speed * dt / 16);
    let lift = 0;
    if (moving) lift = Math.abs(Math.sin(t / 70)) * 0.02;
    if (f.mode === "party") lift = Math.abs(Math.sin(t / 130)) * 0.5;
    if (f.mode === "press") lift = -0.03;
    fly.position.set(f.x, 1.27 + lift, 0.45); fly.rotation.y = f.yaw;
    animateFly(t, moving, f.mode);
    for (const side of ["LEFT", "RIGHT"]) { const b = buttons[side], down = S.pressed === side && now() < S.pressUntil; b.cap.position.y += ((down ? 0.06 : 0.12) - b.cap.position.y) * 0.4; b.cap.material.emissiveIntensity = down ? 1.2 : 0.15; }
    animateCNS(t, dt);
    for (let i = S.confetti.length - 1; i >= 0; i--) { const m = S.confetti[i]; m.position.y -= m.userData.v * dt; m.rotation.x += m.userData.r; m.rotation.y += m.userData.r * 0.7; if (m.position.y < 0.9) { scene.remove(m); S.confetti.splice(i, 1); } }
    // bubble follows the fly's head
    headPos.set(f.x, 1.24 + lift + 0.42, 0.45).project(camera);
    const b = $("#bubble"); b.style.left = ((headPos.x + 1) / 2 * 100) + "%"; b.style.top = ((1 - headPos.y) / 2 * 100) + "%";
    $("#tape").innerHTML = S.tape ? S.tape.replace(/([0-9a-f]{12,}…?)/g, "<span>$1</span>") : "…";
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }

  // --------------------------------------------------------------- boot
  async function boot() {
    const idx = await (await fetch("/api/index")).json();
    S.manifest = idx.manifest; S.events = buildEvents(idx.chain);
    const run = idx.chain.find((e) => e.kind === "run_header"); S.run = run ? run.artifact : null;
    if (S.manifest) $("#disclosure").textContent = S.manifest.disclosure;
    $("#run-id").textContent = S.run ? S.run.run_id : "no run";
    const bd = $("#backend"); bd.textContent = S.run ? S.run.backend : ""; bd.className = "badge " + (S.run && S.run.backend === "fixture-brain-v1" ? "warn" : "ok");
    fetch("/api/verify").then((r) => r.json()).then((rep) => { const w = $("#verify"); w.textContent = (rep.ok ? "VERIFIED " : "VERIFY FAILED ") + rep.checks.length + " checks"; w.className = "badge " + (rep.ok ? "ok" : "bad"); });
    await loadAtlas(S.run);
    S.tape = `run ${S.run ? S.run.run_id : "?"} · manifest ${idx.manifest_sha256 ? idx.manifest_sha256.slice(0, 16) + "…" : "—"} · ${S.events.length} events on the chain`;
    $("#progress").textContent = `${S.events.length} events`;
    $("#play").onclick = () => {
      if (S.i >= S.events.length) { S.i = 0; S.coin = null; S.launch = null; S.fly.mode = "idle"; screenMat.map = null; screenMat.color.set(0x05070c); screenMat.needsUpdate = true; setActivity(null); showReadout(null); }
      S.playing = !S.playing; $("#play").textContent = S.playing ? "⏸ pause" : "▶ play"; if (S.playing) play();
    };
    $("#step").onclick = async () => { if (running || S.i >= S.events.length) return; S.playing = false; $("#play").textContent = "▶ play"; running = true; await runEvent(S.events[S.i]); S.i++; running = false; $("#progress").textContent = `event ${S.i}/${S.events.length}`; };
    $("#end").onclick = skipToEnd;
    $("#speed").onchange = (e) => (S.speed = parseFloat(e.target.value));
    requestAnimationFrame(loop);
    S.playing = true; $("#play").textContent = "⏸ pause"; play();
  }
  boot().catch((e) => { $("#tape").textContent = "ERROR " + e; console.error(e); });
})();
