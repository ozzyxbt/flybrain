/* three.js replay of a hash-chained run.
   Desk, monitor (the exact trial frame as a texture), LEFT/RIGHT buttons, a
   smooth fly; and beside it fixed frontal/dorsal CNS projections where every
   positioned soma is a dim point and the cells that fired in the current
   trial light up from the recorded spike counts. */
(function () {
  const stage = document.getElementById("stage3d");
  if (!stage) return;
  const $ = (s) => document.querySelector(s);
  if (!window.THREE) { $("#tape").textContent = "three.js failed to load (/static/vendor/three.min.js)"; return; }
  const T = window.THREE;

  // ------------------------------------------------------------ renderer
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  stage.prepend(renderer.domElement);
  const scene = new T.Scene();
  scene.background = new T.Color(0x05070c);
  scene.fog = new T.Fog(0x05070c, 7, 14);
  const camera = new T.PerspectiveCamera(38, 16 / 9, 0.1, 50);
  camera.position.set(0, 2.35, 4.9);
  camera.lookAt(0, 1.35, -0.3);
  function resize() {
    const w = stage.clientWidth, h = Math.round(w * 9 / 16);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize); resize();

  // ------------------------------------------------------------- lights
  scene.add(new T.HemisphereLight(0x8fa8d8, 0x0b0e14, 0.55));
  const key = new T.DirectionalLight(0xffffff, 1.1);
  key.position.set(2.5, 5, 3); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.camera.near = 1; key.shadow.camera.far = 15;
  key.shadow.camera.left = -4; key.shadow.camera.right = 4; key.shadow.camera.top = 4; key.shadow.camera.bottom = -2;
  scene.add(key);
  const glow = new T.PointLight(0xdbe5f9, 0.5, 4); glow.position.set(0, 1.9, -0.2); scene.add(glow);
  const rim = new T.DirectionalLight(0xd1f6e0, 0.9); rim.position.set(-3, 3, -4); scene.add(rim);
  const spot = new T.SpotLight(0xfff3d6, 3.2, 8, 0.5, 0.6, 1.2); spot.position.set(0.4, 4.2, 1.6); spot.target.position.set(0, 1.2, 0.45); spot.castShadow = true; scene.add(spot, spot.target);
  const fill = new T.DirectionalLight(0xf5ffe5, 0.35); fill.position.set(3, 2, 4); scene.add(fill);

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

  function label(text, w, h, color, x, y, z) {
    const c = document.createElement("canvas"); c.width = 512; c.height = 64;
    const cx = c.getContext("2d"); cx.font = "bold 30px ui-monospace, Menlo, monospace"; cx.textAlign = "center"; cx.textBaseline = "middle"; cx.fillStyle = color; cx.fillText(text, 256, 34);
    const tex = new T.CanvasTexture(c); tex.colorSpace = T.SRGBColorSpace;
    const s = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    s.scale.set(w, h, 1); s.position.set(x, y, z); return s;
  }

  // ---------------------------------------------------------------- fly
  const fly = new T.Group(); scene.add(fly);
  const flyParts = {};
  // Original low-poly Drosophila: faceted flat-shaded parts, +x is forward.
  const flat = (color, extra = {}) => new T.MeshStandardMaterial({ color, flatShading: true, roughness: 0.55, metalness: 0.28, ...extra });
  const ico = (sx, sy, sz, mat, x, y, z, parent, detail = 2) => { const m = new T.Mesh(new T.IcosahedronGeometry(1, detail), mat); m.position.set(x, y, z); m.scale.set(sx, sy, sz); m.castShadow = true; parent.add(m); return m; };
  const rodGeo = new T.CylinderGeometry(0.85, 1, 1, 6);
  function rod(parent, a, b, radius, mat) { const m = new T.Mesh(rodGeo, mat); m.castShadow = true; parent.add(m); place(m, a, b, radius); return m; }
  const _a = new T.Vector3(), _b = new T.Vector3(), _m = new T.Vector3(), _up = new T.Vector3(0, 1, 0);
  function place(mesh, a, b, radius) {
    _a.set(a[0], a[1], a[2]); _b.set(b[0], b[1], b[2]);
    _m.addVectors(_a, _b).multiplyScalar(0.5); mesh.position.copy(_m);
    _b.sub(_a); const len = _b.length(); mesh.scale.set(radius, len, radius);
    mesh.quaternion.setFromUnitVectors(_up, _b.normalize());
  }
  const seed = (n) => { const x = Math.sin(n * 91.7 + 17.3) * 43758.5453; return x - Math.floor(x); };
  (function buildFly() {
    const shell = flat(0x3a505a), shellLight = flat(0x54687a), dark = flat(0x161d22, { metalness: 0.12 });
    const eyeMat = flat(0xa5183a, { roughness: 0.3, metalness: 0.4, emissive: 0x3a0512, emissiveIntensity: 0.45 });
    const chitin = flat(0x24363d, { metalness: 0.22, roughness: 0.6 });
    // abdomen with segment rings
    ico(0.46, 0.2, 0.22, chitin, -0.4, -0.01, 0, fly);
    for (let i = 0; i < 4; i++) { const ring = new T.Mesh(new T.TorusGeometry(0.19 - i * 0.02, 0.018, 4, 14), flat([0x33484a, 0x3d4a42, 0x2f4448, 0x3a4340][i])); ring.position.set(-0.3 - i * 0.09, 0, 0); ring.rotation.y = Math.PI / 2; ring.scale.z = 0.95; ring.castShadow = true; fly.add(ring); }
    // thorax and bristles
    ico(0.34, 0.27, 0.26, shell, -0.02, 0.05, 0, fly);
    for (let i = 0; i < 48; i++) { const a = seed(i) * Math.PI * 2, b = seed(i + 100) * Math.PI * 0.5; const px = -0.02 + Math.cos(a) * Math.sin(b) * 0.33, py = 0.05 + Math.cos(b) * 0.27, pz = Math.sin(a) * Math.sin(b) * 0.25; rod(fly, [px, py, pz], [px * 1.1 + 0.02, py + 0.05 + seed(i + 7) * 0.04, pz * 1.12], 0.004, dark); }
    // head: faceted, big compound eyes, ocelli, antennae, proboscis
    const head = new T.Group(); head.position.set(0.32, 0.1, 0); fly.add(head); flyParts.head = head;
    ico(0.2, 0.19, 0.19, shellLight, 0, 0, 0, head);
    for (const side of [1, -1]) {
      ico(0.14, 0.18, 0.125, eyeMat, 0.06, 0.02, 0.14 * side, head, 2);
      ico(0.03, 0.022, 0.022, flat(0xe7a8a0, { roughness: 0.15, emissive: 0x7a3f55 }), 0.1, 0.12, 0.23 * side, head, 1);
      rod(head, [0.14, 0.14, 0.06 * side], [0.3, 0.26, 0.15 * side], 0.007, dark);
      ico(0.02, 0.014, 0.014, dark, 0.3, 0.26, 0.15 * side, head, 1);
    }
    rod(head, [0.12, -0.1, 0], [0.24, -0.2, 0], 0.024, shell); ico(0.03, 0.04, 0.055, dark, 0.24, -0.2, 0, head, 1);
    // wings: veined translucent fans on pivots at the roots
    const wingMat = flat(0xa9dce2, { transparent: true, opacity: 0.45, side: T.DoubleSide, roughness: 0.2, metalness: 0.5 });
    const veinMat = new T.MeshStandardMaterial({ color: 0x77999b, transparent: true, opacity: 0.7, metalness: 0.5 });
    flyParts.wings = [];
    for (const side of [1, -1]) {
      const pivot = new T.Group(); pivot.position.set(-0.1, 0.22, 0.12 * side); fly.add(pivot);
      const pts = [[0, 0, 0], [-0.38, 0.03, 0.2 * side], [-0.88, 0.0, 0.56 * side], [-1.04, -0.02, 0.54 * side], [-1.13, -0.02, 0.42 * side], [-0.9, -0.015, 0.21 * side], [-0.34, -0.008, 0.015 * side]];
      const verts = []; for (let i = 1; i < pts.length - 1; i++) verts.push(...pts[0], ...pts[i], ...pts[i + 1]);
      const geo = new T.BufferGeometry(); geo.setAttribute("position", new T.Float32BufferAttribute(verts, 3)); geo.computeVertexNormals();
      const membrane = new T.Mesh(geo, wingMat); pivot.add(membrane);
      const outline = [...pts, pts[0]]; for (let j = 0; j < outline.length - 1; j++) rod(pivot, outline[j], outline[j + 1], 0.005, veinMat);
      for (let j = 2; j < 6; j++) rod(pivot, [-0.05, 0, 0.012 * side], pts[j], 0.0035, veinMat);
      rod(pivot, [-0.42, 0.005, 0.16 * side], [-0.63, 0.012, 0.36 * side], 0.0035, veinMat);
      flyParts.wings.push({ pivot, side });
    }
    // legs: root -> knee -> ankle -> foot, posed each frame
    const legMat = flat(0x243239, { metalness: 0.38, roughness: 0.48 });
    flyParts.legs = [];
    const roots = [[0.17, -0.08, 0.14], [-0.02, -0.11, 0.16], [-0.22, -0.08, 0.14]];
    for (const side of [1, -1]) roots.forEach((r, k) => {
      const upper = rod(fly, [0, 0, 0], [0, 1, 0], 0.017, legMat), lower = rod(fly, [0, 0, 0], [0, 1, 0], 0.011, legMat), foot = rod(fly, [0, 0, 0], [0, 1, 0], 0.006, dark);
      const knee = ico(0.028, 0.028, 0.028, shell, 0, 0, 0, fly, 1);
      flyParts.legs.push({ root: [r[0], r[1], r[2] * side], side, k, upper, lower, foot, knee, i: flyParts.legs.length });
    });
    fly.scale.setScalar(0.95);
  })();
  function animateFly(t, moving, mode) {
    const flapping = moving || mode === "party" || mode === "press";
    const flap = flapping ? Math.sin(t / 22) * 0.75 : 0.12 + Math.sin(t / 900) * 0.04 + (Math.floor(t / 1600) % 4 === 0 ? Math.sin(t / 26) * 0.5 : 0);
    for (const w of flyParts.wings) w.pivot.rotation.x = -w.side * flap;
    if (flyParts.head) flyParts.head.rotation.y = Math.sin(t / 700) * 0.08;
    for (const L of flyParts.legs) {
      const ph = moving ? t / 55 + L.i * 2.1 : 0;
      const swing = moving ? Math.sin(ph) * 0.1 : 0, up = moving ? Math.max(0, Math.cos(ph)) * 0.06 : 0;
      const r = L.root, s = L.side, spread = 0.36 - Math.abs(L.k - 1) * 0.04;
      const knee = [r[0] + swing * 0.6 + (L.k - 1) * -0.12, r[1] + 0.14, r[2] + s * 0.22];
      const ankle = [r[0] + swing + (L.k - 1) * -0.2, -0.38 + up, r[2] + s * spread];
      const foot = [ankle[0] + 0.12, -0.4 + up * 0.5, ankle[2] + s * 0.04];
      place(L.upper, r, knee, 0.017); place(L.lower, knee, ankle, 0.011); place(L.foot, ankle, foot, 0.006);
      L.knee.position.set(knee[0], knee[1], knee[2]);
    }
  }

  // ---------------------------------------------------------------- CNS
  // Fixed anatomical projections drawn straight into pixel buffers: a dim
  // density silhouette of every positioned soma, the neurons that fired in
  // the current trial in bright colour, and the readout cells as markers.
  const CNS = { n: 0, cells: null, cur: null, target: null, views: [], ok: null, schematic: true, big: false };
  const VIEW_W = 920, VIEW_H = 460; // device pixels; CSS scales to the panel
  function orient(raw, n, okMask, schematic) {
    // Pick axes by extent: the longest span is the brain–nerve-cord axis, shown
    // vertical with the denser (brain) end up; the second is left–right.
    const pos = new Float32Array(n * 3);
    if (schematic) { pos.set(raw.subarray(0, n * 3)); return pos; }
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < n; i++) if (okMask[i]) for (let k = 0; k < 3; k++) { const v = raw[i * 3 + k]; if (v < lo[k]) lo[k] = v; if (v > hi[k]) hi[k] = v; }
    const ext = [0, 1, 2].map((k) => hi[k] - lo[k]);
    const order = [0, 1, 2].sort((a, b) => ext[b] - ext[a]); // [long, mid, short]
    const [L, Mx, Sh] = order;
    const vals = []; for (let i = 0; i < n; i++) if (okMask[i]) vals.push(raw[i * 3 + L]);
    vals.sort((a, b) => a - b); const median = vals[vals.length >> 1], mid = (lo[L] + hi[L]) / 2;
    const flipV = median < mid ? -1 : 1; // denser half (brain) goes up
    for (let i = 0; i < n; i++) { pos[i * 3] = raw[i * 3 + Mx]; pos[i * 3 + 1] = flipV * raw[i * 3 + L]; pos[i * 3 + 2] = raw[i * 3 + Sh]; }
    return pos;
  }
  function makeView(id, pos, okMask, n, hAxis, vAxis, schematic) {
    const canvas = document.getElementById("cns-" + id);
    canvas.width = VIEW_W; canvas.height = VIEW_H;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const img = ctx.createImageData(VIEW_W, VIEW_H);
    let lo = [Infinity, Infinity], hi = [-Infinity, -Infinity];
    for (let i = 0; i < n; i++) if (okMask[i]) { const a = pos[i * 3 + hAxis], b = pos[i * 3 + vAxis]; if (a < lo[0]) lo[0] = a; if (a > hi[0]) hi[0] = a; if (b < lo[1]) lo[1] = b; if (b > hi[1]) hi[1] = b; }
    const pad = 28, sw = VIEW_W - 2 * pad, sh = VIEW_H - 2 * pad;
    const scale = Math.min(sw / (hi[0] - lo[0] || 1), sh / (hi[1] - lo[1] || 1));
    const ox = pad + (sw - (hi[0] - lo[0]) * scale) / 2, oy = pad + (sh - (hi[1] - lo[1]) * scale) / 2;
    const pix = new Int32Array(n).fill(-1);
    const density = new Float32Array(VIEW_W * VIEW_H);
    for (let i = 0; i < n; i++) {
      if (!okMask[i]) continue;
      const x = Math.round(ox + (pos[i * 3 + hAxis] - lo[0]) * scale), y = Math.round(oy + (hi[1] - pos[i * 3 + vAxis]) * scale);
      if (x < 1 || y < 1 || x >= VIEW_W - 1 || y >= VIEW_H - 1) continue;
      pix[i] = y * VIEW_W + x;
      density[pix[i]] += 1; density[pix[i] + 1] += 0.5; density[pix[i] + VIEW_W] += 0.5;
    }
    const base = new Uint8ClampedArray(VIEW_W * VIEW_H * 4);
    const gain = schematic ? 60 : 26;
    for (let k = 0; k < VIEW_W * VIEW_H; k++) {
      const d = density[k]; const g = d ? Math.min(150, 34 + d * gain) : 0;
      base[k * 4] = g * 0.72; base[k * 4 + 1] = g * 0.8; base[k * 4 + 2] = g * 0.86; base[k * 4 + 3] = 255;
    }
    return { id, canvas, ctx, img, pix, base };
  }
  async function loadAtlas(run) {
    if (!run || !run.atlas) { $("#brain-title").textContent = "CNS · no atlas in this run"; return; }
    const atlas = await (await fetch("/run/" + run.atlas.path)).json();
    const raw = new Float32Array(await (await fetch("/run/" + atlas.positions_path)).arrayBuffer());
    const n = atlas.n; CNS.n = n; CNS.cells = atlas.cells; CNS.schematic = atlas.schematic; CNS.big = n >= 1000;
    const okMask = new Uint8Array(n); let ok = 0;
    for (let i = 0; i < n; i++) if (Number.isFinite(raw[i * 3]) && Number.isFinite(raw[i * 3 + 1]) && Number.isFinite(raw[i * 3 + 2])) { okMask[i] = 1; ok++; }
    CNS.ok = okMask;
    const pos = orient(raw, n, okMask, atlas.schematic);
    CNS.views = [makeView("frontal", pos, okMask, n, 0, 1, atlas.schematic), makeView("dorsal", pos, okMask, n, 0, 2, atlas.schematic)];
    CNS.target = new Float32Array(n); CNS.cur = new Float32Array(n);
    CNS.hi = [];
    for (const [kind, idxs] of [["left", atlas.cells.left], ["right", atlas.cells.right], ["gate", atlas.cells.gate]]) for (const i of idxs) CNS.hi.push({ i, kind });
    $("#brain-title").textContent = "CNS · " + (atlas.schematic ? "SCHEMATIC LAYOUT (fixture)" : "MaleCNS v1.0 soma positions") + " · " + (atlas.schematic ? n : ok.toLocaleString()) + " annotated somata";
    $("#brain-note").textContent = atlas.note;
    setActivity(null);
  }
  function setActivity(counts) {
    if (!CNS.target) return;
    let max = 1, firing = 0;
    if (counts) for (let i = 0; i < CNS.n; i++) { if (counts[i] > max) max = counts[i]; if (counts[i] > 0) firing++; }
    const lmax = Math.log1p(max);
    for (let i = 0; i < CNS.n; i++) CNS.target[i] = counts ? Math.log1p(counts[i]) / lmax : 0;
    $("#brain-stats").textContent = counts ? `${firing.toLocaleString()} of ${CNS.n.toLocaleString()} cells fired · max ${max} spikes / ${S.readout ? S.readout.neural_window_ms : 500} ms` : "no trial loaded";
  }
  const COLORS = { fire: [200, 236, 70], left: [56, 189, 248], right: [56, 189, 248], gate: [251, 191, 36] };
  function stamp(px, idx, rgb, a, r) {
    // additive blob of radius r pixels around idx
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      const k = (idx + dy * VIEW_W + dx) * 4; if (k < 0 || k >= px.length) continue;
      const f = a * (1 - (Math.abs(dx) + Math.abs(dy)) / (2 * r + 1));
      px[k] = Math.min(255, px[k] + rgb[0] * f); px[k + 1] = Math.min(255, px[k + 1] + rgb[1] * f); px[k + 2] = Math.min(255, px[k + 2] + rgb[2] * f);
    }
  }
  function animateCNS(t, dt) {
    if (!CNS.views.length) return;
    const n = CNS.n, cur = CNS.cur, tg = CNS.target;
    const k = Math.min(1, dt / 200);
    for (let i = 0; i < n; i++) cur[i] += (tg[i] - cur[i]) * k;
    const r = CNS.big ? 1 : 3;
    for (const v of CNS.views) {
      const px = v.img.data; px.set(v.base);
      for (let i = 0; i < n; i++) {
        const c = cur[i]; if (c < 0.03) continue;
        const idx = v.pix[i]; if (idx < 0) continue;
        const a = (CNS.big ? 0.55 * c * c + 0.15 * c : c) * (0.85 + 0.15 * Math.sin(t / 60 + i));
        stamp(px, idx, COLORS.fire, a, r);
      }
      for (const h of CNS.hi) {
        const idx = v.pix[h.i]; if (idx < 0) continue;
        stamp(px, idx, COLORS[h.kind], 0.55 + 0.45 * cur[h.i], CNS.big ? 3 : 5);
      }
      v.ctx.putImageData(v.img, 0, 0);
    }
  }
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
