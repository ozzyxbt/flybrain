/* FLYPONG party app: a club-lit beer-pong table, the low-poly fly, and
   fixed CNS activity views beside it. Everything shown is replayed from the
   hash-chained game record served by /api/index. */
(function () {
  const $ = (s) => document.querySelector(s);
  const stage = document.getElementById("stage3d");
  if (!window.THREE || !window.FLYLIB) { $("#state").textContent = "three.js / flylib failed to load"; return; }
  const T = window.THREE, L = window.FLYLIB;
  const { renderer, scene, camera, key, spot } = L.createStage(stage, { background: 0x05020a, exposure: 1.1, fov: 36 });
  camera.position.set(-1.1, 2.7, 4.7); camera.lookAt(0.55, 1.15, -0.7);
  scene.fog = new T.Fog(0x05020a, 8, 16);
  key.intensity = 0.55; spot.intensity = 2.2; spot.color.set(0xfff0ff);
  const M = (o) => new T.MeshStandardMaterial(o);

  // ------------------------------------------------------------- club
  const floor = new T.Mesh(new T.PlaneGeometry(20, 14), M({ color: 0x0a0616, roughness: 0.35, metalness: 0.4 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const grid = new T.GridHelper(20, 40, 0x3b1d6e, 0x1c0e38); grid.position.y = 0.005; scene.add(grid);
  const wall = new T.Mesh(new T.PlaneGeometry(20, 9), M({ color: 0x0b0618, roughness: 1 })); wall.position.set(0, 4.5, -3.6); scene.add(wall);
  for (const [y, c] of [[2.2, 0xff4fd8], [2.35, 0x4ff2ff], [2.5, 0xc8ff5a]]) { const s = new T.Mesh(new T.PlaneGeometry(20, 0.05), M({ color: c, emissive: c, emissiveIntensity: 1.2 })); s.position.set(0, y, -3.59); scene.add(s); }
  // disco lights
  const discoLights = [];
  for (const [c, off] of [[0xff4fd8, 0], [0x4ff2ff, 2.1], [0xc8ff5a, 4.2]]) {
    const l = new T.SpotLight(c, 1.6, 12, 0.35, 0.5, 1.4); l.position.set(0, 4.6, 0); l.target.position.set(0, 0, 0); scene.add(l, l.target); discoLights.push({ l, off });
  }
  const ballMirror = new T.Mesh(new T.SphereGeometry(0.28, 20, 14), M({ color: 0xffffff, metalness: 1, roughness: 0.15, flatShading: true })); ballMirror.position.set(0, 4.3, -0.4); scene.add(ballMirror);
  const chain = new T.Mesh(new T.CylinderGeometry(0.01, 0.01, 1.2, 6), M({ color: 0x8888aa })); chain.position.set(0, 5.0, -0.4); scene.add(chain);
  // table (long axis z), neon edge
  const table = new T.Mesh(new T.BoxGeometry(2.4, 0.12, 5.2), M({ color: 0x142a5a, roughness: 0.6 })); table.position.set(0, 0.84, -0.5); table.castShadow = true; table.receiveShadow = true; scene.add(table);
  const edge = new T.Mesh(new T.BoxGeometry(2.52, 0.06, 5.32), M({ color: 0x4ff2ff, emissive: 0x4ff2ff, emissiveIntensity: 0.9 })); edge.position.set(0, 0.79, -0.5); scene.add(edge);
  for (const [x, z] of [[-1.05, 1.9], [1.05, 1.9], [-1.05, -2.9], [1.05, -2.9]]) { const leg = new T.Mesh(new T.BoxGeometry(0.12, 0.8, 0.12), M({ color: 0x0f0a22 })); leg.position.set(x, 0.4, z); scene.add(leg); }
  const midline = new T.Mesh(new T.PlaneGeometry(2.3, 0.03), M({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.5 })); midline.rotation.x = -Math.PI / 2; midline.position.set(0, 0.905, -0.5); scene.add(midline);
  // cups
  const cupGeo = new T.CylinderGeometry(0.16, 0.12, 0.34, 18);
  const cupMat = M({ color: 0xe11d48, roughness: 0.4 }), rimMat = M({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.3 });
  const cups = new Map();
  const cupKey = (c) => c[0] + "," + c[1];
  const cupPos = (c) => [parseFloat(c[0]) * 0.8, -1.5 - c[1] * 0.4];
  function makeCup(c) {
    const g = new T.Group(); const [x, z] = cupPos(c); g.position.set(x, 0.9, z);
    const body = new T.Mesh(cupGeo, cupMat); body.position.y = 0.17; body.castShadow = true; g.add(body);
    const rim = new T.Mesh(new T.TorusGeometry(0.16, 0.015, 8, 24), rimMat); rim.rotation.x = Math.PI / 2; rim.position.y = 0.34; g.add(rim);
    const beer = new T.Mesh(new T.CircleGeometry(0.145, 18), M({ color: 0xffb84f, emissive: 0xffb84f, emissiveIntensity: 0.35 })); beer.rotation.x = -Math.PI / 2; beer.position.y = 0.335; g.add(beer);
    scene.add(g); return g;
  }
  const beer = new T.Group(); beer.position.set(0.95, 0.9, 1.35); scene.add(beer);
  { const b = new T.Mesh(new T.CylinderGeometry(0.2, 0.15, 0.42, 18), M({ color: 0xffb84f, transparent: true, opacity: 0.85, roughness: 0.3 })); b.position.y = 0.21; b.castShadow = true; beer.add(b);
    const foam = new T.Mesh(new T.CylinderGeometry(0.21, 0.21, 0.06, 18), M({ color: 0xfff7e0 })); foam.position.y = 0.45; beer.add(foam); }
  const ball = new T.Mesh(new T.SphereGeometry(0.06, 16, 12), M({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.4 })); ball.castShadow = true; ball.visible = false; scene.add(ball);
  const flyRig = L.buildFly(scene);
  const fly = flyRig.group;

  // -------------------------------------------------- CNS + meter
  const { CNS, loadAtlas, animateCNS } = L;
  function setActivity(counts) {
    L.setActivity(counts);
    if (!counts) { $("#m-firing").innerHTML = "— <small id=\"m-pct\"></small>"; $("#m-bar").style.width = "0"; $("#m-note").textContent = `cells with ≥ 1 spike in the ${S.run ? S.run.rules.window_ms : 500} ms window`; return; }
    let firing = 0, max = 0, total = 0;
    for (let i = 0; i < counts.length; i++) { const v = counts[i]; if (v > 0) firing++; if (v > max) max = v; total += v; }
    const pct = 100 * firing / counts.length;
    $("#m-firing").innerHTML = `${firing.toLocaleString()} <small id="m-pct">of ${counts.length.toLocaleString()} · ${pct.toFixed(1)}%</small>`;
    $("#m-bar").style.width = Math.min(100, pct * (counts.length >= 1000 ? 4 : 1)) + "%";
    $("#m-note").textContent = `cells with ≥ 1 spike in the ${S.run.rules.window_ms} ms window · max ${max} spikes · ${total.toLocaleString()} total`;
  }

  // ------------------------------------------------------------- state
  const S = { events: [], i: 0, playing: false, speed: 1, fly: { x: 0, target: 0, yaw: Math.PI / 2, targetYaw: Math.PI / 2, mode: "idle", drunk: 0 }, ball: null, splashes: [], confetti: [], run: null, cups: 6, drinks: 0, hits: 0, hot: 0 };
  const now = () => performance.now();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms / S.speed));
  function say(t, ms) { const b = $("#bubble"); b.textContent = t; b.style.display = "block"; clearTimeout(say.timer); say.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  function banner(t, color, ms) { const b = $("#banner"); b.textContent = t; b.style.color = color; b.classList.add("on"); clearTimeout(banner.timer); banner.timer = setTimeout(() => b.classList.remove("on"), ms / S.speed); }
  function flash(ms) { const f = $("#flash"); f.classList.add("on"); setTimeout(() => f.classList.remove("on"), ms); }
  function feed(text, cls) { const li = document.createElement("li"); li.textContent = text; li.className = cls || ""; const ul = $("#feed"); ul.prepend(li); while (ul.children.length > 8) ul.lastChild.remove(); }
  function state(t) { $("#state").textContent = t; }
  async function parseNpy(url) { const buf = await (await fetch(url)).arrayBuffer(); const v = new DataView(buf); const major = v.getUint8(6); const hl = major === 1 ? v.getUint16(8, true) : v.getUint32(8, true); return new Int32Array(buf.slice((major === 1 ? 10 : 12) + hl)); }
  const loadImage = (url) => new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; });
  function score(throwNo) {
    $("#s-throw").textContent = throwNo ?? "—"; $("#s-cups").textContent = S.cups; $("#s-hits").textContent = S.hits; $("#s-drinks").textContent = S.drinks;
    $("#s-beers").textContent = "🍺".repeat(S.drinks);
  }
  function readout(a) {
    const Lz = a ? parseFloat(a.left_hz) : 0, R = a ? parseFloat(a.right_hz) : 0, mx = Math.max(Lz, R, 1);
    $("#bar-l").style.width = a ? (100 * Lz / mx) + "%" : "0"; $("#bar-r").style.width = a ? (100 * R / mx) + "%" : "0";
    $("#hz-l").textContent = a ? Lz.toFixed(1) + " Hz" : "—"; $("#hz-r").textContent = a ? R.toFixed(1) + " Hz" : "—";
    $("#readout-note").textContent = a ? `gate ${a.gate_spikes} spike${a.gate_spikes === 1 ? "" : "s"} · R−L ${(R - Lz).toFixed(1)} Hz · zero ${parseFloat(a.bias_hz).toFixed(1)} · aim ${parseFloat(a.landing_x).toFixed(2)}` : "gate — · aim —";
    const hz = a ? parseFloat(a.reward_hz) : 0;
    $("#dopa-hz").innerHTML = a ? `${hz.toFixed(1)} <small>Hz</small>` : "— <small>Hz</small>";
    $("#dopa-note").textContent = a ? (a.reward_applied_ms ? `${S.run.reward_cells} PAM11 neurons · reward current on for ${a.reward_applied_ms} ms after the hit · ${a.reward_spikes} spikes` : `${S.run.reward_cells} PAM11 neurons · no reward current this throw · ${a.reward_spikes} spikes`) : "15 PAM11 neurons · reward current after a hit";
    $(".card.dopa").classList.toggle("hot", !!(a && a.reward_applied_ms));
    $("#dopa-ring").style.transform = `rotate(${Math.min(360, hz * 6)}deg)`;
  }
  function setCups(list) { const want = new Set(list.map(cupKey)); for (const [k, g] of cups) if (!want.has(k)) { scene.remove(g); cups.delete(k); } for (const c of list) if (!cups.has(cupKey(c))) cups.set(cupKey(c), makeCup(c)); S.cups = list.length; }
  function spawnConfetti(n) { for (let k = 0; k < n; k++) { const m = new T.Mesh(new T.BoxGeometry(0.04, 0.06, 0.01), new T.MeshBasicMaterial({ color: [0xc8ff5a, 0x4ff2ff, 0xff4fd8, 0xffb84f][k % 4] })); m.position.set((Math.random() - 0.5) * 5, 3.5 + Math.random() * 1.5, (Math.random() - 0.5) * 4 - 0.5); m.userData = { v: 0.01 + Math.random() * 0.02, r: Math.random() * 0.2 }; scene.add(m); S.confetti.push(m); } }
  function splash(x, z) { const m = new T.Mesh(new T.RingGeometry(0.05, 0.2, 24), new T.MeshBasicMaterial({ color: 0xffb84f, transparent: true, opacity: 0.9, side: T.DoubleSide })); m.rotation.x = -Math.PI / 2; m.position.set(x, 1.25, z); scene.add(m); S.splashes.push({ mesh: m, t0: now() }); }

  // ------------------------------------------------------------- events
  async function showFrame(a) { const img = await loadImage("/run/" + a.frame_path); if (img) { const c = $("#flycam").getContext("2d"); c.imageSmoothingEnabled = false; c.drawImage(img, 0, 0, 320, 180); } }
  async function runThrow(a) {
    state(`THROW ${a.throw} · ${a.cups_before.length} cups · ${a.drinks_before} drinks`);
    setCups(a.cups_before); S.drinks = a.drinks_before; S.fly.drunk = Math.min(1.5, a.drinks_before * 0.3); score(a.throw);
    S.fly.target = 0; S.fly.mode = "idle";
    const [, spikes] = await Promise.all([showFrame(a), parseNpy("/run/" + a.spike_path)]);
    say(a.drinks_before >= 4 ? "*hic* …which cup…" : a.drinks_before >= 2 ? "two tables? ok." : "focus.", 900);
    await sleep(400);
    setActivity(spikes); readout(a);
    $("#cns-rates").textContent = `DNp20 L ${parseFloat(a.left_hz).toFixed(1)} · R ${parseFloat(a.right_hz).toFixed(1)} Hz · gate ${a.gate_spikes}`;
    if (a.reward_applied_ms) { S.hot = now(); flash(500); banner(`✨ DOPAMINE · PAM11 ${parseFloat(a.reward_hz).toFixed(1)} Hz`, "#ff4fd8", 1600); feed(`✨ dopamine: PAM11 ${parseFloat(a.reward_hz).toFixed(1)} Hz after the hit`, "dopa"); S.fly.mode = "party"; await sleep(900); S.fly.mode = "idle"; }
    await sleep(500);
    const lx = parseFloat(a.landing_x) * 0.8, tz = a.hit ? cupPos(a.cup)[1] : -2.65;
    S.ball = { t0: now(), dur: 1100 / S.speed, from: [fly.position.x + 0.35, 1.55, 0.45], to: [lx, a.hit ? 1.25 : 0.96, tz], hit: a.hit };
    ball.visible = true; S.fly.mode = "press"; say(a.gate_spikes ? "THROW!" : "…gate silent", 800);
    await sleep(1150); ball.visible = false; S.fly.mode = "idle";
    if (a.hit) {
      const g = cups.get(cupKey(a.cup)); if (g) { splash(g.position.x, g.position.z); g.userData.sink = now(); }
      S.hits++; spawnConfetti(80); flash(300);
      banner(`🎯 HIT · cup ${a.cup[0]} row ${a.cup[1]}`, "#c8ff5a", 1400); feed(`🎯 throw ${a.throw}: hit cup (${a.cup[0]}, row ${a.cup[1]})`, "hit");
      say("LET'S GOOO", 1200); S.fly.mode = "party"; await sleep(1200); S.fly.mode = "idle";
      setCups(a.cups_after); score(a.throw);
    } else {
      banner(a.gate_spikes ? `💨 miss · landed at ${parseFloat(a.landing_x).toFixed(2)}` : "💨 miss · no gate spike, no throw", "#ffb84f", 1400);
      feed(`🍺 throw ${a.throw}: miss → drink #${a.drinks_after}`, "miss");
      say("ugh. drink.", 1000);
      S.fly.target = 0.62; S.fly.mode = "walk"; await sleep(900);
      S.fly.mode = "drink"; say("*glug glug*", 1300); await sleep(1300);
      S.drinks = a.drinks_after; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(a.throw);
      say(S.drinks >= 4 ? "*hic*" : S.drinks >= 2 ? "whoa." : "fine.", 900);
      S.fly.mode = "idle"; S.fly.target = 0; await sleep(700);
    }
  }
  async function runEvent(ev) {
    const a = ev.a;
    if (ev.type === "calibration") {
      state("CALIBRATING · empty table");
      const [, spikes] = await Promise.all([showFrame(a), parseNpy("/run/" + a.spike_path)]);
      setActivity(spikes); $("#cns-rates").textContent = `calibration · L ${parseFloat(a.left_hz).toFixed(1)} · R ${parseFloat(a.right_hz).toFixed(1)} Hz`; $("#hz-l").textContent = parseFloat(a.left_hz).toFixed(1) + " Hz"; $("#hz-r").textContent = parseFloat(a.right_hz).toFixed(1) + " Hz";
      $("#readout-note").textContent = `calibration · R−L ${parseFloat(a.bias_hz).toFixed(1)} Hz becomes the aim zero`;
      banner(`🎯 calibration · aim zero ${parseFloat(a.bias_hz).toFixed(1)} Hz`, "#4ff2ff", 2000); feed(`🎯 calibration on the empty table: aim zero ${parseFloat(a.bias_hz).toFixed(1)} Hz`);
      say("empty table. noted.", 1500); await sleep(2000); return;
    }
    if (ev.type === "throw") return runThrow(a);
    if (ev.type === "result") {
      state(a.result);
      banner(`${a.result === "TABLE CLEARED" ? "🏆" : a.result === "PASSED OUT" ? "😵" : "⏱"} ${a.result} · ${a.hits}/${a.throws} · ${a.drinks} drinks`, a.result === "TABLE CLEARED" ? "#c8ff5a" : "#ffb84f", 6000);
      feed(`${a.result}: ${a.hits} hits in ${a.throws} throws, ${a.drinks} drinks`);
      if (a.result === "TABLE CLEARED") { S.fly.mode = "party"; spawnConfetti(200); say("TABLE CLEARED!!!", 4000); }
      else if (a.result === "PASSED OUT") { S.fly.mode = "passout"; say("zzz…", 5000); }
      else { S.fly.mode = "shrug"; say("out of throws.", 4000); }
      await sleep(3000);
    }
  }
  let running = false;
  async function play() {
    if (running) return; running = true;
    while (S.playing && S.i < S.events.length) { $("#progress").textContent = `${S.i + 1}/${S.events.length}`; await runEvent(S.events[S.i]); S.i++; }
    if (S.i >= S.events.length) { S.playing = false; $("#play").textContent = "↺ replay"; }
    running = false;
  }
  function reset() { S.i = 0; S.drinks = 0; S.hits = 0; S.fly.drunk = 0; S.fly.mode = "idle"; fly.rotation.z = 0; setCups(S.run.rules.cups); score(null); setActivity(null); readout(null); $("#feed").innerHTML = ""; state("ready"); }
  function skipToEnd() {
    S.playing = false;
    const last = [...S.events].reverse().find((e) => e.type === "throw"), res = S.events.find((e) => e.type === "result");
    if (last) { setCups(last.a.cups_after); S.drinks = last.a.drinks_after; S.hits = S.events.filter((e) => e.type === "throw" && e.a.hit).length; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(last.a.throw); parseNpy("/run/" + last.a.spike_path).then(setActivity); readout(last.a); showFrame(last.a); }
    if (res) runEvent(res);
    S.i = S.events.length; $("#play").textContent = "↺ replay"; $("#progress").textContent = `${S.events.length}/${S.events.length}`;
  }

  // --------------------------------------------------------------- loop
  let last = now(); const headPos = new T.Vector3();
  function loop(t) {
    const dt = Math.min(50, t - last); last = t;
    const f = S.fly, dx = f.target - f.x, moving = Math.abs(dx) > 0.02;
    const stagger = f.drunk ? Math.sin(t / 180) * 0.012 * f.drunk : 0;
    if (moving) f.x += Math.sign(dx) * Math.min(Math.abs(dx), (0.022 - 0.006 * Math.min(1, f.drunk)) * S.speed * dt / 16) + stagger;
    if (moving) f.targetYaw = dx > 0 ? 0 : Math.PI; else if (f.mode === "party") f.targetYaw = f.yaw + 0.1 * S.speed; else if (f.mode === "drink") f.targetYaw = 0; else f.targetYaw = Math.PI / 2;
    let dyaw = ((f.targetYaw - f.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    f.yaw += Math.abs(dyaw) < 0.02 ? dyaw : Math.sign(dyaw) * Math.min(Math.abs(dyaw), 0.16 * S.speed * dt / 16);
    let lift = 0, pitch = 0;
    if (moving) lift = Math.abs(Math.sin(t / 70)) * 0.02;
    if (f.mode === "party") lift = Math.abs(Math.sin(t / 130)) * 0.45;
    if (f.mode === "press") { lift = 0.08; pitch = -0.35; }
    if (f.mode === "drink") pitch = 0.55 + Math.sin(t / 150) * 0.05;
    fly.position.set(f.x, 1.27 + lift, 0.45); fly.rotation.y = f.yaw;
    flyRig.animate(t, moving, f.mode, f.mode === "passout" ? 0 : f.drunk);
    if (f.mode === "passout") fly.rotation.z = Math.PI * 0.5; else fly.rotation.x += pitch;
    if (S.ball) { const b = S.ball, u = Math.min(1, (now() - b.t0) / b.dur); ball.position.set(b.from[0] + (b.to[0] - b.from[0]) * u, b.from[1] + (b.to[1] - b.from[1]) * u + Math.sin(u * Math.PI) * 1.1, b.from[2] + (b.to[2] - b.from[2]) * u); ball.rotation.x += 0.2; if (u >= 1) S.ball = null; }
    for (const [, g] of cups) if (g.userData.sink) { const u = Math.min(1, (now() - g.userData.sink) / 600); g.scale.set(1 - u * 0.4, 1 - u, 1 - u * 0.4); }
    for (let i = S.splashes.length - 1; i >= 0; i--) { const s = S.splashes[i], u = (now() - s.t0) / 700; if (u >= 1) { scene.remove(s.mesh); S.splashes.splice(i, 1); continue; } s.mesh.scale.setScalar(1 + u * 3); s.mesh.material.opacity = 0.9 * (1 - u); }
    for (let i = S.confetti.length - 1; i >= 0; i--) { const m = S.confetti[i]; m.position.y -= m.userData.v * dt; m.rotation.x += m.userData.r; m.rotation.y += m.userData.r * 0.7; if (m.position.y < 0.05) { scene.remove(m); S.confetti.splice(i, 1); } }
    // disco: sweeping coloured spots, faster and pinker while dopamine is on
    const hot = now() - S.hot < 2500 ? 1 : 0;
    discoLights.forEach(({ l, off }, i) => { const a = t / (hot ? 700 : 2200) + off; l.target.position.set(Math.cos(a) * 2.2, 0.9, Math.sin(a) * 1.8 - 0.5); l.intensity = (hot ? 2.6 : 1.4) + Math.sin(t / 300 + i) * 0.3; });
    ballMirror.rotation.y = t / 4000;
    animateCNS(t, dt);
    headPos.set(f.x, 1.27 + lift + 0.42, 0.45).project(camera);
    const bb = $("#bubble"); bb.style.left = ((headPos.x + 1) / 2 * 100) + "%"; bb.style.top = ((1 - headPos.y) / 2 * 100) + "%";
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }

  // --------------------------------------------------------------- boot
  async function boot() {
    const idx = await (await fetch("/api/index")).json();
    const run = idx.chain.find((e) => e.kind === "pong_header");
    if (!run) { state("not a beer-pong game directory"); return; }
    S.run = run.artifact;
    S.events = idx.chain.filter((e) => ["calibration", "throw", "pong_result"].includes(e.kind)).map((e) => ({ type: e.kind === "throw" ? "throw" : e.kind === "calibration" ? "calibration" : "result", a: e.artifact, sha: e.sha256 }));
    $("#disclosure").textContent = S.run.disclosure + " Every frame, spike array and readout on this page is read from the hash-chained game record (" + S.run.run_id + ").";
    const cb = $("#chip-backend"); cb.textContent = S.run.backend === "fixture-brain-v1" ? "FIXTURE BRAIN" : "MaleCNS CONNECTOME"; cb.className = "chip " + (S.run.backend === "fixture-brain-v1" ? "warn" : "ok");
    const cc = $("#chip-chain"); cc.textContent = idx.chain_error ? "CHAIN BROKEN" : `CHAIN OK · ${idx.chain.length}`; cc.className = "chip " + (idx.chain_error ? "warn" : "ok");
    $("#chip-mode").textContent = "REPLAY · " + S.run.run_id;
    CNS.windowMs = S.run.rules.window_ms;
    await loadAtlas(S.run);
    reset();
    $("#play").onclick = () => { if (S.i >= S.events.length) reset(); S.playing = !S.playing; $("#play").textContent = S.playing ? "⏸ pause" : "▶ play"; if (S.playing) play(); };
    $("#step").onclick = async () => { if (running || S.i >= S.events.length) return; S.playing = false; $("#play").textContent = "▶ play"; running = true; await runEvent(S.events[S.i]); S.i++; running = false; };
    $("#end").onclick = skipToEnd;
    document.querySelectorAll("[data-speed]").forEach((b) => (b.onclick = () => { S.speed = parseFloat(b.dataset.speed); document.querySelectorAll("[data-speed]").forEach((x) => x.classList.toggle("on", x === b)); }));
    requestAnimationFrame(loop);
    S.playing = true; $("#play").textContent = "⏸ pause"; play();
  }
  boot().catch((e) => { state("ERROR " + e); console.error(e); });
})();
