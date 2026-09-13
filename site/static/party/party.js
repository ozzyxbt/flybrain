/* FLYPONG party app: a club-lit beer-pong table, the low-poly fly, and
   fixed CNS activity views beside it. Everything shown is replayed from the
   hash-chained game record served by /api/index. */
(function () {
  const $ = (s) => document.querySelector(s);
  const stage = document.getElementById("stage3d");
  if (!window.THREE || !window.FLYLIB) { $("#state").textContent = "three.js / flylib failed to load"; return; }
  const T = window.THREE, L = window.FLYLIB;
  const { renderer, scene, camera, key, spot } = L.createStage(stage, { background: 0x3a2a5e, exposure: 1.15, fov: 30, fill: true });
  camera.position.set(1.2, 3.9, -9.0); camera.lookAt(-0.1, 1.0, 0.7);
  scene.fog = new T.Fog(0x4a3470, 9, 20);
  key.intensity = 0.7; key.color.set(0xffd9c2); spot.intensity = 2.0; spot.color.set(0xffe0f0);
  const M = (o) => new T.MeshStandardMaterial(o);

  // ------------------------------------------------------------- club
  const floor = new T.Mesh(new T.PlaneGeometry(20, 14), M({ color: 0x2c2150, roughness: 0.4, metalness: 0.35 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const grid = new T.GridHelper(20, 40, 0x8a5aa8, 0x4a3a78); grid.position.y = 0.005; scene.add(grid);
  // sunset backdrop behind the bar: coral sky, big low sun, palm silhouettes
  const sky = document.createElement("canvas"); sky.width = 1024; sky.height = 512;
  { const g = sky.getContext("2d"); const grad = g.createLinearGradient(0, 0, 0, 512); grad.addColorStop(0, "#eb9998"); grad.addColorStop(0.35, "#d98aa9"); grad.addColorStop(0.62, "#a373c0"); grad.addColorStop(0.85, "#6f70a2"); grad.addColorStop(1, "#5d649c"); g.fillStyle = grad; g.fillRect(0, 0, 1024, 512);
    const sun = g.createRadialGradient(560, 330, 10, 560, 330, 150); sun.addColorStop(0, "#fff0c8"); sun.addColorStop(0.35, "#ffc2a0"); sun.addColorStop(1, "rgba(255,170,160,0)"); g.fillStyle = sun; g.fillRect(360, 150, 400, 380);
    g.fillStyle = "#ffdcb0"; g.beginPath(); g.arc(560, 330, 62, 0, Math.PI * 2); g.fill();
    for (let i = 0; i < 5; i++) { g.fillStyle = "rgba(93,100,156,0.55)"; g.fillRect(0, 300 + i * 12, 1024, 3); }
    g.fillStyle = "#3a2a5e";
    const palm = (x, h, lean) => { g.beginPath(); g.moveTo(x, 512); g.quadraticCurveTo(x + lean * 0.5, 512 - h * 0.6, x + lean, 512 - h); g.lineTo(x + lean + 8, 512 - h); g.quadraticCurveTo(x + lean * 0.5 + 8, 512 - h * 0.6, x + 10, 512); g.fill();
      for (let a = -2.6; a <= 0.4; a += 0.45) { g.beginPath(); g.ellipse(x + lean + 4 + Math.cos(a) * 40, 512 - h - 4 + Math.sin(a) * 26, 46, 9, a, 0, Math.PI * 2); g.fill(); } };
    palm(120, 300, 28); palm(250, 230, -18); palm(820, 320, -30); palm(940, 240, 14);
    g.fillStyle = "#3a2a5e"; for (let x = 0; x < 1024; x += 1) { const h = 20 + 18 * Math.abs(Math.sin(x * 0.02)) + 10 * Math.abs(Math.sin(x * 0.11)); g.fillRect(x, 512 - h, 1, h); } }
  const skyTex = new T.CanvasTexture(sky); skyTex.colorSpace = T.SRGBColorSpace;
  const wall = new T.Mesh(new T.PlaneGeometry(20, 10), new T.MeshBasicMaterial({ map: skyTex })); wall.position.set(0, 4.5, 3.62); wall.rotation.y = Math.PI; scene.add(wall);
  for (const [y, c] of [[2.2, 0xeb9998], [2.35, 0xffd27a], [2.5, 0xa373c0]]) { const s = new T.Mesh(new T.PlaneGeometry(20, 0.05), M({ color: c, emissive: c, emissiveIntensity: 1.2 })); s.position.set(0, y, 3.59); s.rotation.y = Math.PI; scene.add(s); }
  // bar counter, shelves and bottles behind the fly; hanging lamps over the table
  const counter = new T.Mesh(new T.BoxGeometry(7.5, 1.05, 0.9), M({ color: 0x4a2a55, roughness: 0.5, metalness: 0.2 })); counter.position.set(0, 0.52, 3.0); counter.castShadow = true; scene.add(counter);
  const counterTop = new T.Mesh(new T.BoxGeometry(7.6, 0.06, 1.0), M({ color: 0xffd27a, emissive: 0xffb98a, emissiveIntensity: 0.5 })); counterTop.position.set(0, 1.07, 3.0); scene.add(counterTop);
  for (const y of [1.9, 2.55]) { const shelf = new T.Mesh(new T.BoxGeometry(6.4, 0.05, 0.35), M({ color: 0x5a3a6a })); shelf.position.set(0, y, 3.42); scene.add(shelf);
    const glowStrip = new T.Mesh(new T.PlaneGeometry(6.4, 0.03), M({ color: 0xeb9998, emissive: 0xeb9998, emissiveIntensity: 1.5 })); glowStrip.position.set(0, y - 0.03, 3.24); scene.add(glowStrip); }
  // back-bar: mirror panel with warm backlight, real bottle silhouettes with labels, hanging glasses
  const backPanel = new T.Mesh(new T.PlaneGeometry(6.6, 1.9), M({ color: 0x7e3a63, metalness: 0.6, roughness: 0.3, transparent: true, opacity: 0.85 })); backPanel.position.set(0, 2.55, 3.58); backPanel.rotation.y = Math.PI; scene.add(backPanel);
  for (let i = 0; i < 7; i++) { const bl = new T.Mesh(new T.PlaneGeometry(0.04, 1.8), M({ color: 0xffb84f, emissive: 0xffb84f, emissiveIntensity: 0.9, transparent: true, opacity: 0.55 })); bl.position.set(-3.0 + i * 1.0, 2.55, 3.57); bl.rotation.y = Math.PI; scene.add(bl); }
  const bottleColors = [0x1f7a3a, 0xb86a1c, 0x8a1c2c, 0x2b5fb8, 0x5a2a8a, 0xd9c47a, 0x1d7c86, 0x9b3d5a, 0x6b8f2a, 0xc0562b];
  const glassMat = (col) => new T.MeshPhysicalMaterial({ color: col, transparent: true, opacity: 0.72, roughness: 0.12, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.1 });
  const seedB = (n) => { const x = Math.sin(n * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
  for (let i = 0; i < 22; i++) {
    const shelfY = i < 11 ? 1.925 : 2.575, x = -2.95 + (i % 11) * 0.59 + (i >= 11 ? 0.28 : 0), col = bottleColors[(i * 7) % bottleColors.length];
    const h = 0.34 + seedB(i) * 0.22, r = 0.05 + seedB(i + 40) * 0.02, mat = glassMat(col);
    const body = new T.Mesh(new T.CylinderGeometry(r, r * 1.02, h, 14), mat); body.position.set(x, shelfY + h / 2, 3.42); body.castShadow = true; scene.add(body);
    const shoulder = new T.Mesh(new T.CylinderGeometry(0.018, r, 0.09, 14), mat); shoulder.position.set(x, shelfY + h + 0.045, 3.42); scene.add(shoulder);
    const neckH = 0.14 + seedB(i + 80) * 0.1; const neck = new T.Mesh(new T.CylinderGeometry(0.018, 0.018, neckH, 10), mat); neck.position.set(x, shelfY + h + 0.09 + neckH / 2, 3.42); scene.add(neck);
    const cap = new T.Mesh(new T.CylinderGeometry(0.022, 0.022, 0.035, 10), M({ color: [0x111111, 0xd4af37, 0xeeeeee][i % 3], metalness: 0.6, roughness: 0.3 })); cap.position.set(x, shelfY + h + 0.09 + neckH + 0.017, 3.42); scene.add(cap);
    const label = new T.Mesh(new T.PlaneGeometry(r * 1.9, h * 0.42), M({ color: [0xf5efe0, 0x1a1a1a, 0xe8d8b0][i % 3], roughness: 0.9 })); label.position.set(x, shelfY + h * 0.45, 3.42 - r - 0.002); label.rotation.y = Math.PI; scene.add(label);
    const liquid = new T.Mesh(new T.CylinderGeometry(r * 0.92, r * 0.94, h * (0.35 + seedB(i + 9) * 0.5), 12), M({ color: col, transparent: true, opacity: 0.85, roughness: 0.3 })); liquid.position.set(x, shelfY + liquid.geometry.parameters.height / 2 + 0.01, 3.42); scene.add(liquid);
  }
  // hanging glasses under the top shelf
  for (let i = 0; i < 9; i++) { const g = new T.Mesh(new T.CylinderGeometry(0.075, 0.03, 0.16, 12, 1, true), new T.MeshPhysicalMaterial({ color: 0xdfe9ff, transparent: true, opacity: 0.35, roughness: 0.05, side: T.DoubleSide })); g.position.set(-2.4 + i * 0.6, 2.42, 3.3); g.rotation.x = Math.PI; scene.add(g); }
  // beer tap on the counter, and two stools
  const tapBase = new T.Mesh(new T.CylinderGeometry(0.06, 0.09, 0.42, 12), M({ color: 0xd4d4dc, metalness: 0.9, roughness: 0.25 })); tapBase.position.set(-2.2, 1.31, 2.75); scene.add(tapBase);
  const tapArm = new T.Mesh(new T.CylinderGeometry(0.025, 0.025, 0.32, 8), M({ color: 0xd4d4dc, metalness: 0.9, roughness: 0.25 })); tapArm.position.set(-2.2, 1.52, 2.6); tapArm.rotation.x = Math.PI / 2.4; scene.add(tapArm);
  const tapHandle = new T.Mesh(new T.CylinderGeometry(0.035, 0.05, 0.22, 10), M({ color: 0xeb9998, emissive: 0xeb9998, emissiveIntensity: 0.4 })); tapHandle.position.set(-2.2, 1.62, 2.72); scene.add(tapHandle);
  for (const x of [-1.2, 2.2]) { const seat = new T.Mesh(new T.CylinderGeometry(0.28, 0.28, 0.08, 20), M({ color: 0xd11f3a, roughness: 0.55 })); seat.position.set(x, 0.72, 2.25); seat.castShadow = true; scene.add(seat);
    const post = new T.Mesh(new T.CylinderGeometry(0.04, 0.04, 0.7, 8), M({ color: 0xd4d4dc, metalness: 0.9, roughness: 0.3 })); post.position.set(x, 0.35, 2.25); scene.add(post);
    const foot = new T.Mesh(new T.CylinderGeometry(0.24, 0.24, 0.03, 20), M({ color: 0xd4d4dc, metalness: 0.9, roughness: 0.3 })); foot.position.set(x, 0.015, 2.25); scene.add(foot); }
  const signCanvas = document.createElement("canvas"); signCanvas.width = 512; signCanvas.height = 128; { const cx = signCanvas.getContext("2d"); cx.font = "900 92px Inter, system-ui, sans-serif"; cx.textAlign = "center"; cx.textBaseline = "middle"; cx.shadowColor = "#ff7ab6"; cx.shadowBlur = 30; cx.fillStyle = "#fff4f1"; cx.fillText("FLY", 170, 64); cx.shadowColor = "#ffd27a"; cx.fillStyle = "#ffd27a"; cx.fillText("PONG", 380, 64); }
  const signTex = new T.CanvasTexture(signCanvas); signTex.colorSpace = T.SRGBColorSpace;
  const sign = new T.Mesh(new T.PlaneGeometry(3.2, 0.8), new T.MeshBasicMaterial({ map: signTex, transparent: true })); sign.position.set(0, 3.25, 3.55); sign.rotation.y = Math.PI; scene.add(sign);
  for (const x of [-1.6, 0, 1.6]) { const cord = new T.Mesh(new T.CylinderGeometry(0.008, 0.008, 1.2, 4), M({ color: 0x555577 })); cord.position.set(x, 4.4, -0.6); scene.add(cord);
    const shade = new T.Mesh(new T.ConeGeometry(0.28, 0.22, 16, 1, true), M({ color: 0x1f1538, side: T.DoubleSide })); shade.position.set(x, 3.75, -0.6); scene.add(shade);
    const bulb = new T.Mesh(new T.SphereGeometry(0.06, 10, 8), M({ color: 0xfff1c0, emissive: 0xffd27a, emissiveIntensity: 2 })); bulb.position.set(x, 3.68, -0.6); scene.add(bulb);
    const pl = new T.PointLight(0xffd27a, 0.7, 4); pl.position.set(x, 3.6, -0.6); scene.add(pl); }
  // disco lights
  const discoLights = [];
  for (const [c, off] of [[0xeb9998, 0], [0xa373c0, 2.1], [0xffd27a, 4.2]]) {
    const l = new T.SpotLight(c, 1.6, 12, 0.35, 0.5, 1.4); l.position.set(0, 4.6, 0); l.target.position.set(0, 0, 0); scene.add(l, l.target); discoLights.push({ l, off });
  }
  const ballMirror = new T.Mesh(new T.SphereGeometry(0.28, 20, 14), M({ color: 0xffffff, metalness: 1, roughness: 0.15, flatShading: true })); ballMirror.position.set(0, 4.3, -0.4); scene.add(ballMirror);
  const chain = new T.Mesh(new T.CylinderGeometry(0.01, 0.01, 1.2, 6), M({ color: 0x8888aa })); chain.position.set(0, 5.0, -0.4); scene.add(chain);
  // table (long axis z), neon edge
  const table = new T.Mesh(new T.BoxGeometry(2.4, 0.12, 5.2), M({ color: 0x1f7a4a, roughness: 0.65 })); table.position.set(0, 0.84, -0.5); table.castShadow = true; table.receiveShadow = true; scene.add(table);
  const edge = new T.Mesh(new T.BoxGeometry(2.52, 0.06, 5.32), M({ color: 0xeb9998, emissive: 0xeb9998, emissiveIntensity: 0.9 })); edge.position.set(0, 0.79, -0.5); scene.add(edge);
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
    const beer = new T.Mesh(new T.CircleGeometry(0.145, 18), M({ color: 0xffd21a, emissive: 0xffc107, emissiveIntensity: 0.5 })); beer.rotation.x = -Math.PI / 2; beer.position.y = 0.335; g.add(beer);
    scene.add(g); return g;
  }
  const BEER = [0.98, -0.2];
  const beer = new T.Group(); beer.position.set(BEER[0], 0.9, BEER[1]); scene.add(beer);
  const beerLiquid = new T.Mesh(new T.CylinderGeometry(0.2, 0.15, 0.42, 18), M({ color: 0xffd21a, emissive: 0xffb300, emissiveIntensity: 0.35, transparent: true, opacity: 0.92, roughness: 0.25 })); beerLiquid.position.y = 0.21; beerLiquid.castShadow = true; beer.add(beerLiquid);
  const beerGlass = new T.Mesh(new T.CylinderGeometry(0.21, 0.16, 0.46, 18, 1, true), new T.MeshPhysicalMaterial({ color: 0xdfe9ff, transparent: true, opacity: 0.25, roughness: 0.05, side: T.DoubleSide })); beerGlass.position.y = 0.23; beer.add(beerGlass);
  const foam = new T.Mesh(new T.CylinderGeometry(0.21, 0.21, 0.07, 18), M({ color: 0xfffbea, roughness: 0.9 })); foam.position.y = 0.45; beer.add(foam);
  const ball = new T.Mesh(new T.SphereGeometry(0.06, 16, 12), M({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.4 })); ball.castShadow = true; ball.visible = false; scene.add(ball);
  const flyRig = L.buildFly(scene);
  const fly = flyRig.group;
  // rig: position + yaw + nose pitch (about the fly's lateral axis); the inner group keeps the drunk sway
  const rig = new T.Group(); rig.rotation.order = "YZX"; scene.add(rig); rig.add(fly);
  fly.scale.setScalar(0.95 * 0.85 * 0.9);
  const FLY_Z = 1.15; // near the fly's end of the table
  const f_z = () => S.fly.z;

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
  const S = { gen: 0, events: [], i: 0, playing: false, speed: 1, collapse: 0, fly: { x: 0, z: 1.15, target: 0, tz: 1.15, yaw: Math.PI / 2, targetYaw: Math.PI / 2, mode: "idle", drunk: 0 }, ball: null, splashes: [], confetti: [], run: null, cups: 6, drinks: 0, hits: 0, hot: 0 };
  const now = () => performance.now();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms / S.speed));
  function say(t, ms) { const b = $("#bubble"); b.textContent = t; b.style.display = "block"; clearTimeout(say.timer); say.timer = setTimeout(() => (b.style.display = "none"), ms / S.speed); }
  function banner(t, color, ms) { const b = $("#banner"); b.textContent = t; b.style.color = color; b.classList.add("on"); clearTimeout(banner.timer); banner.timer = setTimeout(() => b.classList.remove("on"), ms / S.speed); }
  function flash(ms) { const f = $("#flash"); f.classList.add("on"); setTimeout(() => f.classList.remove("on"), ms); }
  function feed(text, cls) { const ul = $("#feed"); if (!ul) return; const li = document.createElement("li"); li.textContent = text; li.className = cls || ""; ul.prepend(li); while (ul.children.length > 8) ul.lastChild.remove(); }
  let state = (t) => { const el = $("#state"); if (el) el.textContent = t; };
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
    const dop = $(".dopa"); if (dop) dop.classList.toggle("hot", !!(a && a.reward_applied_ms));
    const ring = $("#dopa-ring"); if (ring) ring.style.transform = `rotate(${Math.min(360, hz * 6)}deg)`;
  }
  function setCups(list) { const want = new Set(list.map(cupKey)); for (const [k, g] of cups) if (!want.has(k)) { scene.remove(g); cups.delete(k); } for (const c of list) if (!cups.has(cupKey(c))) cups.set(cupKey(c), makeCup(c)); S.cups = list.length; }
  function spawnConfetti(n) { for (let k = 0; k < n; k++) { const m = new T.Mesh(new T.BoxGeometry(0.04, 0.06, 0.01), new T.MeshBasicMaterial({ color: [0xffd27a, 0xa373c0, 0xeb9998, 0xfff4f1][k % 4] })); m.position.set((Math.random() - 0.5) * 5, 3.5 + Math.random() * 1.5, (Math.random() - 0.5) * 4 - 0.5); m.userData = { v: 0.01 + Math.random() * 0.02, r: Math.random() * 0.2 }; scene.add(m); S.confetti.push(m); } }
  function splash(x, z) { const m = new T.Mesh(new T.RingGeometry(0.05, 0.2, 24), new T.MeshBasicMaterial({ color: 0xffb84f, transparent: true, opacity: 0.9, side: T.DoubleSide })); m.rotation.x = -Math.PI / 2; m.position.set(x, 1.25, z); scene.add(m); S.splashes.push({ mesh: m, t0: now() }); }

  // ------------------------------------------------------------- events
  async function showFrame(a) { const img = await loadImage("run/" + a.frame_path); if (img) { const c = $("#flycam").getContext("2d"); c.imageSmoothingEnabled = false; c.drawImage(img, 0, 0, 320, 180); } }
  async function runThrow(a) {
    const g = S.gen;
    state(`THROW ${a.throw} · ${a.cups_before.length} cups · ${a.drinks_before} drinks`);
    setCups(a.cups_before); S.drinks = a.drinks_before; S.fly.drunk = Math.min(1.5, a.drinks_before * 0.3); score(a.throw);
    S.fly.target = 0; S.fly.tz = FLY_Z; S.fly.mode = "idle";
    const [, spikes] = await Promise.all([showFrame(a), parseNpy("run/" + a.spike_path)]);
    if (g !== S.gen) return;
    say(a.drinks_before >= 4 ? "*hic* …which cup…" : a.drinks_before >= 2 ? "two tables? ok." : "focus.", 900);
    await sleep(400);
    if (g !== S.gen) return;
    setActivity(spikes); readout(a);
    $("#cns-rates").textContent = `DNp20 L ${parseFloat(a.left_hz).toFixed(1)} · R ${parseFloat(a.right_hz).toFixed(1)} Hz · gate ${a.gate_spikes}`;
    if (a.reward_applied_ms) { S.hot = now(); flash(500); banner(`✨ DOPAMINE · PAM11 ${parseFloat(a.reward_hz).toFixed(1)} Hz`, "#ff7ab6", 1600); feed(`✨ dopamine: PAM11 ${parseFloat(a.reward_hz).toFixed(1)} Hz after the hit`, "dopa"); S.fly.mode = "party"; await sleep(900); S.fly.mode = "idle"; }
    if (g !== S.gen) return;
    await sleep(500);
    if (g !== S.gen) return;
    const lx = parseFloat(a.landing_x) * 0.8, tz = a.hit ? cupPos(a.cup)[1] : -2.65;
    S.ball = { t0: now(), dur: 1100 / S.speed, from: [rig.position.x, 1.5, f_z() - 0.3], to: [lx, a.hit ? 1.25 : 0.96, tz], hit: a.hit };
    ball.visible = true; S.fly.mode = "press"; say(a.gate_spikes ? "THROW!" : "…gate silent", 800);
    await sleep(1150); ball.visible = false; S.fly.mode = "idle";
    if (g !== S.gen) return;
    if (a.hit) {
      const g = cups.get(cupKey(a.cup)); if (g) { splash(g.position.x, g.position.z); g.userData.sink = now(); }
      S.hits++; spawnConfetti(80); flash(300);
      banner(`🎯 HIT · cup ${a.cup[0]} row ${a.cup[1]}`, "#ffd27a", 1400); feed(`🎯 throw ${a.throw}: hit cup (${a.cup[0]}, row ${a.cup[1]})`, "hit");
      say("LET'S GOOO", 1200); S.fly.mode = "party"; await sleep(1200); S.fly.mode = "idle";
      if (g !== S.gen) return;
      setCups(a.cups_after); score(a.throw);
    } else {
      banner(a.gate_spikes ? `💨 miss · landed at ${parseFloat(a.landing_x).toFixed(2)}` : "💨 miss · no gate spike, no throw", "#ffb84f", 1400);
      feed(`🍺 throw ${a.throw}: miss → drink #${a.drinks_after}`, "miss");
      say("ugh. drink.", 1000);
      // walk to the beer, lean the head into the glass, drink some of it
      S.fly.target = BEER[0] - 0.34; S.fly.tz = BEER[1] + 0.02; S.fly.mode = "walk"; await sleep(1400);
      if (g !== S.gen) return;
      S.fly.mode = "drink"; say("*glug glug*", 1300); beerLiquid.scale.y = Math.max(0.15, 1 - 0.14 * a.drinks_after); beerLiquid.position.y = 0.21 * beerLiquid.scale.y; foam.position.y = 0.42 * beerLiquid.scale.y + 0.03; await sleep(1300);
      if (g !== S.gen) return;
      S.drinks = a.drinks_after; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(a.throw);
      say(S.drinks >= 4 ? "*hic*" : S.drinks >= 2 ? "whoa." : "fine.", 900);
      S.fly.mode = "idle"; S.fly.target = 0; S.fly.tz = FLY_Z; await sleep(700);
      if (g !== S.gen) return;
    }
  }
  async function runEvent(ev) {
    const a = ev.a; const g = S.gen;
    if (ev.type === "calibration") {
      state("CALIBRATING · empty table");
      const [, spikes] = await Promise.all([showFrame(a), parseNpy("run/" + a.spike_path)]);
      if (g !== S.gen) return;
      setActivity(spikes); $("#cns-rates").textContent = `calibration · L ${parseFloat(a.left_hz).toFixed(1)} · R ${parseFloat(a.right_hz).toFixed(1)} Hz`; $("#hz-l").textContent = parseFloat(a.left_hz).toFixed(1) + " Hz"; $("#hz-r").textContent = parseFloat(a.right_hz).toFixed(1) + " Hz";
      $("#readout-note").textContent = `calibration · R−L ${parseFloat(a.bias_hz).toFixed(1)} Hz becomes the aim zero`;
      banner(`🎯 calibration · aim zero ${parseFloat(a.bias_hz).toFixed(1)} Hz`, "#a373c0", 2000); feed(`🎯 calibration on the empty table: aim zero ${parseFloat(a.bias_hz).toFixed(1)} Hz`);
      say("empty table. noted.", 1500); await sleep(2000); return;
    }
    if (ev.type === "throw") return runThrow(a);
    if (ev.type === "result") {
      state(a.result);
      banner(`${a.result === "TABLE CLEARED" ? "🏆" : a.result === "PASSED OUT" ? "😵" : "⏱"} ${a.result} · ${a.hits}/${a.throws} · ${a.drinks} drinks`, a.result === "TABLE CLEARED" ? "#ffd27a" : "#ffb98a", 6000);
      feed(`${a.result}: ${a.hits} hits in ${a.throws} throws, ${a.drinks} drinks`);
      if (a.result === "TABLE CLEARED") { S.fly.mode = "party"; spawnConfetti(200); say("TABLE CLEARED!!!", 4000); }
      else if (a.result === "PASSED OUT") { S.fly.mode = "passout"; say("zzz…", 5000); }
      else { S.fly.mode = "shrug"; say("out of throws.", 4000); }
      await sleep(3000);
      if (g !== S.gen) return;
    }
  }
  let running = false;
  async function play() {
    if (running) return; running = true;
    while (S.playing && S.i < S.events.length) { $("#progress").textContent = `${S.i + 1}/${S.events.length}`; await runEvent(S.events[S.i]); S.i++; }
    if (S.i >= S.events.length) { S.playing = false; $("#play").textContent = "↺ replay"; }
    running = false;
  }
  function reset() { S.gen++; S.i = 0; S.drinks = 0; S.hits = 0; S.fly.drunk = 0; S.fly.mode = "idle"; S.collapse = 0; S.fly.tz = FLY_Z; beerLiquid.scale.y = 1; beerLiquid.position.y = 0.21; foam.position.y = 0.45; setCups(S.run.rules.cups); score(null); setActivity(null); readout(null); $("#feed").innerHTML = ""; state("ready"); }
  function skipToEnd() {
    S.playing = false; S.gen++;
    const last = [...S.events].reverse().find((e) => e.type === "throw"), res = S.events.find((e) => e.type === "result");
    if (last) { setCups(last.a.cups_after); S.drinks = last.a.drinks_after; S.hits = S.events.filter((e) => e.type === "throw" && e.a.hit).length; S.fly.drunk = Math.min(1.5, S.drinks * 0.3); score(last.a.throw); parseNpy("run/" + last.a.spike_path).then(setActivity); readout(last.a); showFrame(last.a); }
    if (res) runEvent(res);
    S.i = S.events.length; $("#play").textContent = "↺ replay"; $("#progress").textContent = `${S.events.length}/${S.events.length}`;
  }

  // --------------------------------------------------------------- loop
  let last = now(); const headPos = new T.Vector3();
  function loop(t) {
    const dt = Math.min(50, t - last); last = t;
    const f = S.fly, dx = f.target - f.x, dz = f.tz - f.z, dist = Math.hypot(dx, dz), moving = dist > 0.02;
    const stagger = f.drunk ? Math.sin(t / 180) * 0.012 * f.drunk : 0;
    if (moving) { const step = Math.min(dist, (0.022 - 0.006 * Math.min(1, f.drunk)) * S.speed * dt / 16); f.x += dx / dist * step + stagger; f.z += dz / dist * step; }
    if (moving) f.targetYaw = Math.atan2(-dz, dx); else if (f.mode === "party") f.targetYaw = f.yaw + 0.1 * S.speed; else if (f.mode === "drink") f.targetYaw = 0; else f.targetYaw = Math.PI / 2;
    let dyaw = ((f.targetYaw - f.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    f.yaw += Math.abs(dyaw) < 0.02 ? dyaw : Math.sign(dyaw) * Math.min(Math.abs(dyaw), 0.16 * S.speed * dt / 16);
    let lift = 0, pitch = 0;
    if (moving) lift = Math.abs(Math.sin(t / 70)) * 0.02;
    if (f.mode === "party") lift = Math.abs(Math.sin(t / 130)) * 0.45;
    if (f.mode === "press") { lift = 0.08; pitch = -0.35; }
    if (f.mode === "drink") { const depth = 1 - beerLiquid.scale.y; pitch = 0.3 + 0.55 * depth + Math.sin(t / 150) * 0.05; lift = 0.02 - 0.06 * depth; }  // dips deeper as the glass empties
    // pass-out: legs splay, body sinks face-down onto the table (no rolling)
    S.collapse += ((f.mode === "passout" ? 1 : 0) - S.collapse) * Math.min(1, dt / 450);
    const c = S.collapse;
    rig.position.set(f.x, 1.25 + lift - 0.18 * c, f.z); rig.rotation.y = f.yaw;
    flyRig.animate(t, moving, f.mode, f.drunk * (1 - c), c);
    rig.rotation.z = -(pitch * (1 - c) + 0.22 * c);
    if (S.ball) { const b = S.ball, u = Math.min(1, (now() - b.t0) / b.dur); ball.position.set(b.from[0] + (b.to[0] - b.from[0]) * u, b.from[1] + (b.to[1] - b.from[1]) * u + Math.sin(u * Math.PI) * 1.1, b.from[2] + (b.to[2] - b.from[2]) * u); ball.rotation.x += 0.2; if (u >= 1) S.ball = null; }
    for (const [, g] of cups) if (g.userData.sink) { const u = Math.min(1, (now() - g.userData.sink) / 600); g.scale.set(1 - u * 0.4, 1 - u, 1 - u * 0.4); }
    for (let i = S.splashes.length - 1; i >= 0; i--) { const s = S.splashes[i], u = (now() - s.t0) / 700; if (u >= 1) { scene.remove(s.mesh); S.splashes.splice(i, 1); continue; } s.mesh.scale.setScalar(1 + u * 3); s.mesh.material.opacity = 0.9 * (1 - u); }
    for (let i = S.confetti.length - 1; i >= 0; i--) { const m = S.confetti[i]; m.position.y -= m.userData.v * dt; m.rotation.x += m.userData.r; m.rotation.y += m.userData.r * 0.7; if (m.position.y < 0.05) { scene.remove(m); S.confetti.splice(i, 1); } }
    // disco: sweeping coloured spots, faster and pinker while dopamine is on
    const hot = now() - S.hot < 2500 ? 1 : 0;
    discoLights.forEach(({ l, off }, i) => { const a = t / (hot ? 700 : 2200) + off; l.target.position.set(Math.cos(a) * 2.2, 0.9, Math.sin(a) * 1.8 - 0.5); l.intensity = (hot ? 2.6 : 1.4) + Math.sin(t / 300 + i) * 0.3; });
    ballMirror.rotation.y = t / 4000;
    animateCNS(t, dt);
    headPos.set(f.x, 1.25 + lift + 0.38, f.z).project(camera);
    const bb = $("#bubble"); bb.style.left = ((headPos.x + 1) / 2 * 100) + "%"; bb.style.top = ((1 - headPos.y) / 2 * 100) + "%";
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }

  // --------------------------------------------------------------- boot
  async function boot() {
    const idx = await (await fetch("api/index.json")).json();
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
    const stateEl = $("#state"); if (stateEl && stateEl.hidden) state = () => {};
    requestAnimationFrame(loop);
    S.playing = true; $("#play").textContent = "⏸ pause"; play();
  }
  boot().catch((e) => { state("ERROR " + e); console.error(e); });
})();
