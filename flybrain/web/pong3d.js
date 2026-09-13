/* Beer pong replay: the fly throws where the recorded DNp20 readout says,
   cups sink on recorded hits, drinks accumulate on misses, PAM11 activity is
   read from the recorded spike arrays. */
(function () {
  const stage = document.getElementById("stage3d");
  if (!stage) return;
  const $ = (s) => document.querySelector(s);
  if (!window.THREE || !window.FLYLIB) { $("#tape").textContent = "three.js / flylib failed to load"; return; }
  const T = window.THREE, L = window.FLYLIB;
  const { renderer, scene, camera } = L.createStage(stage, { background: 0x07110d });
  camera.position.set(-0.3, 2.6, 4.6); camera.lookAt(0.6, 1.1, -0.6);
  const M = (o) => new T.MeshStandardMaterial(o);

  // ---------------------------------------------------------------- room
  const floor = new T.Mesh(new T.PlaneGeometry(16, 12), M({ color: 0x0b1410, roughness: 0.95 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const wall = new T.Mesh(new T.PlaneGeometry(16, 8), M({ color: 0x0a1210, roughness: 1 })); wall.position.set(0, 4, -3.2); scene.add(wall);
  const strip = new T.Mesh(new T.PlaneGeometry(16, 0.08), M({ color: 0xbef264, emissive: 0xbef264, emissiveIntensity: 0.6 })); strip.position.set(0, 2.9, -3.19); scene.add(strip);
  // long table along z: fly end at z=+1.4, cups at z≈-2
  const table = new T.Mesh(new T.BoxGeometry(2.4, 0.12, 5.2), M({ color: 0x1f6f4a, roughness: 0.7 })); table.position.set(0, 0.84, -0.5); table.castShadow = true; table.receiveShadow = true; scene.add(table);
  const edge = new T.Mesh(new T.BoxGeometry(2.5, 0.06, 5.3), M({ color: 0xf1f5f9 })); edge.position.set(0, 0.78, -0.5); scene.add(edge);
  for (const [x, z] of [[-1.05, 1.9], [1.05, 1.9], [-1.05, -2.9], [1.05, -2.9]]) { const leg = new T.Mesh(new T.BoxGeometry(0.12, 0.8, 0.12), M({ color: 0x1a2030 })); leg.position.set(x, 0.4, z); scene.add(leg); }
  const midline = new T.Mesh(new T.PlaneGeometry(2.3, 0.03), M({ color: 0xffffff })); midline.rotation.x = -Math.PI / 2; midline.position.set(0, 0.905, -0.5); scene.add(midline);

  // cups: lateral x in [-1,1] → table x [-0.8, 0.8]; row 0..2 → z from -1.5 to -2.3
  const cupGeo = new T.CylinderGeometry(0.16, 0.12, 0.34, 18);
  const cupMat = M({ color: 0xb91c1c, roughness: 0.45 }), rimMat = M({ color: 0xf8fafc });
  const cups = new Map();
  function cupKey(c) { return c[0] + "," + c[1]; }
  function cupPos(c) { return [parseFloat(c[0]) * 0.8, -1.5 - c[1] * 0.4]; }
  function makeCup(c) {
    const g = new T.Group(); const [x, z] = cupPos(c); g.position.set(x, 0.9, z);
    const body = new T.Mesh(cupGeo, cupMat); body.position.y = 0.17; body.castShadow = true; g.add(body);
    const rim = new T.Mesh(new T.TorusGeometry(0.16, 0.015, 8, 24), rimMat); rim.rotation.x = Math.PI / 2; rim.position.y = 0.34; g.add(rim);
    const beer = new T.Mesh(new T.CircleGeometry(0.145, 18), M({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.25 })); beer.rotation.x = -Math.PI / 2; beer.position.y = 0.335; g.add(beer);
    scene.add(g); return g;
  }
  // fly's own beer at the near-right corner
  const beer = new T.Group(); beer.position.set(0.95, 0.9, 1.35); scene.add(beer);
  { const b = new T.Mesh(new T.CylinderGeometry(0.2, 0.15, 0.42, 18), M({ color: 0xf59e0b, transparent: true, opacity: 0.85, roughness: 0.3 })); b.position.y = 0.21; b.castShadow = true; beer.add(b);
    const foam = new T.Mesh(new T.CylinderGeometry(0.21, 0.21, 0.06, 18), M({ color: 0xfff7e0 })); foam.position.y = 0.45; beer.add(foam);
    beer.add(L.label("BEER", 0.6, 0.08, "#fbbf24", 0, 0.62, 0)); }
  const ball = new T.Mesh(new T.SphereGeometry(0.06, 16, 12), M({ color: 0xf8fafc, roughness: 0.4 })); ball.castShadow = true; ball.visible = false; scene.add(ball);
  const splashGeo = new T.RingGeometry(0.05, 0.2, 24);
  const flyRig = L.buildFly(scene);
  const fly = flyRig.group;
  const { CNS, loadAtlas, setActivity, animateCNS } = L;

  // -------------------------------------------------------------- state
  const S = { events: [], i: 0, playing: false, speed: 1, fly: { x: 0, target: 0, yaw: Math.PI / 2, targetYaw: Math.PI / 2, mode: "idle", drunk: 0 }, ball: null, splashes: [], run: null, tape: "", cups: 6, drinks: 0, lastThrow: null };
  const now = () => performance.now();
  function say(t, ms) { const b = $("#bubble"); b.textContent = t; b.style.display = "block"; clearTimeout(say.timer); say.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  function banner(t, color, ms) { const b = $("#banner"); b.textContent = t; b.style.borderTopColor = color; b.style.color = color; b.style.display = "block"; clearTimeout(banner.timer); banner.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  async function parseNpy(url) { const buf = await (await fetch(url)).arrayBuffer(); const v = new DataView(buf); const major = v.getUint8(6); const hl = major === 1 ? v.getUint16(8, true) : v.getUint32(8, true); return new Int32Array(buf.slice((major === 1 ? 10 : 12) + hl)); }
  function loadImage(url) { return new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; }); }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms / S.speed));
  function score(throwNo) { $("#score").innerHTML = `throw ${throwNo ?? "—"} · cups <b>${S.cups}</b> · <span class="drunk">drinks ${S.drinks}${S.drinks >= 4 ? " · wasted" : S.drinks >= 2 ? " · tipsy" : ""}</span>`; }
  function showReadout(a) {
    $("#cns-rates").textContent = a ? `DNp20 L ${parseFloat(a.left_hz).toFixed(1)} Hz · R ${parseFloat(a.right_hz).toFixed(1)} Hz · gate ${a.gate_spikes}` : "DNp20 L — · R — · gate —";
    $("#dopa-hz").textContent = a ? `${parseFloat(a.reward_hz).toFixed(1)} Hz` : "— Hz";
    $("#dopa-note").textContent = a ? (a.reward_applied_ms ? `${S.run.reward_cells} PAM11 neurons · reward current ${a.reward_applied_ms} ms after the previous hit · ${a.reward_spikes} spikes` : `${S.run.reward_cells} PAM11 neurons · no reward current this throw · ${a.reward_spikes} spikes`) : "";
    $("#dopa-hz").style.color = a && a.reward_applied_ms ? "#e879f9" : "#7d8bab";
  }
  function setCups(list) {
    const want = new Set(list.map(cupKey));
    for (const [k, g] of cups) if (!want.has(k)) { scene.remove(g); cups.delete(k); }
    for (const c of list) if (!cups.has(cupKey(c))) cups.set(cupKey(c), makeCup(c));
    S.cups = list.length;
  }

  // ------------------------------------------------------------- events
  async function runThrow(a) {
    S.tape = `chain · throw ${a.throw} · cups ${a.cups_before.length} · drinks ${a.drinks_before} · input ${a.input_sha256.slice(0, 12)}… spikes ${a.spike_sha256.slice(0, 12)}…`;
    setCups(a.cups_before); S.drinks = a.drinks_before; S.fly.drunk = Math.min(1.5, a.drinks_before * 0.3); score(a.throw);
    S.fly.target = 0; S.fly.mode = "idle";
    const [img, spikes] = await Promise.all([loadImage("/run/" + a.frame_path), parseNpy("/run/" + a.spike_path)]);
    if (img) { const c = $("#flycam").getContext("2d"); c.imageSmoothingEnabled = false; c.drawImage(img, 0, 0, 320, 180); }
    CNS.windowMs = S.run.rules.window_ms;
    say(a.drinks_before >= 4 ? "*hic* …aim…" : a.drinks_before >= 2 ? "hmm… two tables?" : "HMM…", 900);
    await sleep(400);
    setActivity(spikes); showReadout(a);
    $("#spikes-total").textContent = spikes.reduce((s, v) => s + v, 0).toLocaleString();
    $("#spikes-note").textContent = `in ${S.run.rules.window_ms} ms of neural time`;
    if (a.reward_applied_ms) { banner(`DOPAMINE · PAM11 ${parseFloat(a.reward_hz).toFixed(1)} Hz after the hit`, "#e879f9", 1600); S.fly.mode = "party"; await sleep(900); S.fly.mode = "idle"; }
    await sleep(600);
    // throw: ball from the fly's head to the landing spot
    const lx = parseFloat(a.landing_x) * 0.8;
    const targetZ = a.hit ? cupPos(a.cup)[1] : -1.5 - 0.4 * 2 - 0.35;
    S.ball = { t0: now(), dur: 1100 / S.speed, from: [fly.position.x + 0.35, 1.55, 0.45], to: [lx, a.hit ? 1.25 : 0.96, targetZ], hit: a.hit };
    ball.visible = true; S.fly.mode = "press";
    say(a.gate_spikes ? "THROW!" : "…no gate spike", 800);
    await sleep(1150);
    ball.visible = false; S.fly.mode = "idle";
    if (a.hit) {
      const g = cups.get(cupKey(a.cup)); if (g) { S.splashes.push({ mesh: splash(g.position.x, g.position.z), t0: now() }); g.userData.sink = now(); }
      banner(`HIT · cup ${a.cup[0]} row ${a.cup[1]} sinks`, "#bef264", 1400);
      say("YESSS", 1200); S.fly.mode = "party";
      await sleep(1200); S.fly.mode = "idle";
      setCups(a.cups_after); score(a.throw);
    } else {
      banner(a.gate_spikes ? `miss · landed at ${parseFloat(a.landing_x).toFixed(2)} (R−L ${(parseFloat(a.right_hz) - parseFloat(a.left_hz)).toFixed(1)} Hz, zero ${parseFloat(a.bias_hz).toFixed(1)})` : "miss · gate silent, no throw registered", "#fb7185", 1400);
      say("ugh. drink.", 1000);
      // walk to the beer, tilt, drink
      S.fly.target = 0.62; S.fly.mode = "walk"; await sleep(900);
      S.fly.mode = "drink"; say("*glug glug*", 1300); await sleep(1300);
      S.drinks = a.drinks_after; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(a.throw);
      say(S.drinks >= 4 ? "*hic*" : S.drinks >= 2 ? "whoa." : "ok.", 900);
      S.fly.mode = "idle"; S.fly.target = 0; await sleep(700);
    }
    S.lastThrow = a;
  }
  function splash(x, z) { const m = new T.Mesh(splashGeo, M({ color: 0xf59e0b, transparent: true, opacity: 0.8, side: T.DoubleSide })); m.rotation.x = -Math.PI / 2; m.position.set(x, 1.25, z); scene.add(m); return m; }
  async function runEvent(ev) {
    if (ev.type === "throw") return runThrow(ev.a);
    if (ev.type === "calibration") {
      const a = ev.a;
      S.tape = `chain · calibration on the empty table · L ${a.left_hz} R ${a.right_hz} · aim zero ${a.bias_hz} Hz`;
      const [img, spikes] = await Promise.all([loadImage("/run/" + a.frame_path), parseNpy("/run/" + a.spike_path)]);
      if (img) { const c = $("#flycam").getContext("2d"); c.imageSmoothingEnabled = false; c.drawImage(img, 0, 0, 320, 180); }
      setActivity(spikes); $("#cns-rates").textContent = `calibration · DNp20 L ${parseFloat(a.left_hz).toFixed(1)} Hz · R ${parseFloat(a.right_hz).toFixed(1)} Hz`;
      banner(`CALIBRATION · empty table · right − left = ${parseFloat(a.bias_hz).toFixed(1)} Hz becomes the aim zero`, "#38bdf8", 2200);
      say("empty table. noted.", 1500);
      await sleep(2200);
      return;
    }
    if (ev.type === "result") {
      const a = ev.a;
      S.tape = `chain · result ${a.result} · ${a.hits} hits / ${a.throws} throws · ${a.drinks} drinks · ${ev.sha.slice(0, 16)}…`;
      banner(`${a.result} · ${a.hits} hits / ${a.throws} throws · ${a.drinks} drinks`, a.result === "TABLE CLEARED" ? "#bef264" : "#fbbf24", 5000);
      if (a.result === "TABLE CLEARED") { S.fly.mode = "party"; say("TABLE CLEARED!!!", 4000); }
      else if (a.result === "PASSED OUT") { S.fly.mode = "passout"; say("zzz…", 5000); }
      else { S.fly.mode = "shrug"; say("out of throws.", 4000); }
      await sleep(3000);
    }
  }
  let running = false;
  async function play() {
    if (running) return; running = true;
    while (S.playing && S.i < S.events.length) { $("#progress").textContent = `event ${S.i + 1}/${S.events.length}`; await runEvent(S.events[S.i]); S.i++; }
    if (S.i >= S.events.length) { S.playing = false; $("#play").textContent = "↺ replay"; $("#progress").textContent = `done · ${S.events.length} events`; }
    running = false;
  }
  function reset() { S.i = 0; S.drinks = 0; S.fly.drunk = 0; S.fly.mode = "idle"; setCups(S.run.rules.cups); score(null); setActivity(null); showReadout(null); }
  function skipToEnd() {
    S.playing = false;
    const last = [...S.events].reverse().find((e) => e.type === "throw"), res = S.events.find((e) => e.type === "result");
    if (last) { setCups(last.a.cups_after); S.drinks = last.a.drinks_after; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(last.a.throw); parseNpy("/run/" + last.a.spike_path).then(setActivity); showReadout(last.a); loadImage("/run/" + last.a.frame_path).then((img) => { if (img) $("#flycam").getContext("2d").drawImage(img, 0, 0, 320, 180); }); }
    if (res) runEvent(res);
    S.i = S.events.length; $("#play").textContent = "↺ replay"; $("#progress").textContent = `done · ${S.events.length} events`;
  }

  // --------------------------------------------------------------- loop
  let last = now();
  const headPos = new T.Vector3();
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
    if (f.mode === "drink") { pitch = 0.55 + Math.sin(t / 150) * 0.05; }
    if (f.mode === "passout") { pitch = 0; fly.rotation.z = Math.PI * 0.5; }
    fly.position.set(f.x, 1.27 + lift, 0.45); fly.rotation.y = f.yaw;
    flyRig.animate(t, moving, f.mode, f.mode === "passout" ? 0 : f.drunk);
    if (f.mode !== "passout") fly.rotation.x += pitch;
    // ball flight
    if (S.ball) {
      const b = S.ball, u = Math.min(1, (now() - b.t0) / b.dur);
      const x = b.from[0] + (b.to[0] - b.from[0]) * u, z = b.from[2] + (b.to[2] - b.from[2]) * u;
      const y = b.from[1] + (b.to[1] - b.from[1]) * u + Math.sin(u * Math.PI) * 1.1;
      ball.position.set(x, y, z); ball.rotation.x += 0.2;
      if (u >= 1) { if (!b.hit) { ball.position.y = 0.96; } S.ball = null; }
    }
    for (const [k, g] of cups) if (g.userData.sink) { const u = Math.min(1, (now() - g.userData.sink) / 600); g.scale.set(1 - u * 0.4, 1 - u, 1 - u * 0.4); }
    for (let i = S.splashes.length - 1; i >= 0; i--) { const s = S.splashes[i], u = (now() - s.t0) / 700; if (u >= 1) { scene.remove(s.mesh); S.splashes.splice(i, 1); continue; } s.mesh.scale.setScalar(1 + u * 3); s.mesh.material.opacity = 0.8 * (1 - u); }
    animateCNS(t, dt);
    headPos.set(f.x, 1.27 + lift + 0.42, 0.45).project(camera);
    const bb = $("#bubble"); bb.style.left = ((headPos.x + 1) / 2 * 100) + "%"; bb.style.top = ((1 - headPos.y) / 2 * 100) + "%";
    $("#tape").innerHTML = S.tape ? S.tape.replace(/([0-9a-f]{12,}…?)/g, "<span>$1</span>") : "…";
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }

  // --------------------------------------------------------------- boot
  async function boot() {
    const idx = await (await fetch("/api/index")).json();
    const run = idx.chain.find((e) => e.kind === "pong_header");
    if (!run) { $("#tape").textContent = "This run directory is not a beer-pong game (serve one made with `flybrain pong`)."; return; }
    S.run = run.artifact;
    S.events = idx.chain.filter((e) => ["throw", "pong_result", "calibration"].includes(e.kind)).map((e) => ({ type: e.kind === "throw" ? "throw" : e.kind === "calibration" ? "calibration" : "result", a: e.artifact, sha: e.sha256 }));
    $("#disclosure").textContent = S.run.disclosure;
    $("#run-id").textContent = S.run.run_id;
    const bd = $("#backend"); bd.textContent = S.run.backend; bd.className = "badge " + (S.run.backend === "fixture-brain-v1" ? "warn" : "ok");
    const vb = $("#verify"); vb.textContent = idx.chain_error ? "CHAIN BROKEN" : `CHAIN OK · ${idx.chain.length} entries`; vb.className = "badge " + (idx.chain_error ? "bad" : "ok");
    await loadAtlas(S.run);
    reset();
    S.tape = `game ${S.run.run_id} · ${S.events.length - 1} throws recorded · press play`;
    $("#progress").textContent = `${S.events.length} events`;
    $("#play").onclick = () => { if (S.i >= S.events.length) reset(); S.playing = !S.playing; $("#play").textContent = S.playing ? "⏸ pause" : "▶ play"; if (S.playing) play(); };
    $("#step").onclick = async () => { if (running || S.i >= S.events.length) return; S.playing = false; $("#play").textContent = "▶ play"; running = true; await runEvent(S.events[S.i]); S.i++; running = false; $("#progress").textContent = `event ${S.i}/${S.events.length}`; };
    $("#end").onclick = skipToEnd;
    $("#speed").onchange = (e) => (S.speed = parseFloat(e.target.value));
    requestAnimationFrame(loop);
    S.playing = true; $("#play").textContent = "⏸ pause"; play();
  }
  boot().catch((e) => { $("#tape").textContent = "ERROR " + e; console.error(e); });
})();
