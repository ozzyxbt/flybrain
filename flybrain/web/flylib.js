/* Shared three.js building blocks for the FLYBRAIN pages: stage + lights,
   the original low-poly fly, and the CNS activity views. Exposed as
   window.FLYLIB; pages compose them. */
(function () {
  const $ = (s) => document.querySelector(s);
  const T = window.THREE;
  if (!T) { window.FLYLIB = null; return; }

  function createStage(stage, opts = {}) {
    const renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = opts.exposure || 1.05;
    stage.prepend(renderer.domElement);
    const scene = new T.Scene();
    scene.background = new T.Color(opts.background ?? 0x05070c);
    scene.fog = new T.Fog(opts.background ?? 0x05070c, 7, 14);
    const camera = new T.PerspectiveCamera(opts.fov || 38, 16 / 9, 0.1, 50);
    function resize() {
      const w = stage.clientWidth, h = opts.fill ? stage.clientHeight : Math.round(w * 9 / 16);
      renderer.setSize(w, h, false);
      camera.aspect = w / h; camera.updateProjectionMatrix();
    }
    window.addEventListener("resize", resize); resize();
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

    return { renderer, scene, camera, resize, key, spot };
  }

  function label(text, w, h, color, x, y, z) {
    const c = document.createElement("canvas"); c.width = 512; c.height = 64;
    const cx = c.getContext("2d"); cx.font = "bold 30px ui-monospace, Menlo, monospace"; cx.textAlign = "center"; cx.textBaseline = "middle"; cx.fillStyle = color; cx.fillText(text, 256, 34);
    const tex = new T.CanvasTexture(c); tex.colorSpace = T.SRGBColorSpace;
    const s = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    s.scale.set(w, h, 1); s.position.set(x, y, z); return s;
  }

  function buildFly(scene) {
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
    const eyeMat = flat(0xa5183a, { roughness: 0.3, metalness: 0.4, emissive: 0x3a0512, emissiveIntensity: 0.45 }); flyParts.eyeMat = eyeMat;
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
  function animateFly(t, moving, mode, drunk = 0, collapse = 0) {
    const flapping = moving || mode === "party" || mode === "press";
    const flap = flapping ? Math.sin(t / 22) * 0.75 : 0.12 + Math.sin(t / 900) * 0.04 + (Math.floor(t / 1600) % 4 === 0 ? Math.sin(t / 26) * 0.5 : 0);
    for (const w of flyParts.wings) w.pivot.rotation.x = (-w.side * flap + (drunk ? Math.sin(t / 140 + w.side) * 0.08 * drunk : 0)) * (1 - collapse) + (-w.side * 0.95) * collapse;
    // flies have no eyelids; asleep, the eyes only dim for a relaxed look
    if (flyParts.eyeMat) flyParts.eyeMat.emissiveIntensity = 0.45 * (1 - 0.7 * collapse);
    if (flyParts.head) { flyParts.head.rotation.y = (Math.sin(t / 700) * 0.08 + (drunk ? Math.sin(t / 230) * 0.12 * drunk : 0)) * (1 - collapse); flyParts.head.rotation.z = (drunk ? Math.sin(t / 310) * 0.1 * drunk : 0) * (1 - collapse); flyParts.head.rotation.x = 0.35 * collapse; }
    fly.rotation.z = drunk ? Math.sin(t / 420) * 0.05 * drunk : 0;
    fly.rotation.x = drunk ? Math.sin(t / 530) * 0.03 * drunk : 0;
    for (const L of flyParts.legs) {
      const ph = moving ? t / 55 + L.i * 2.1 : 0;
      const swing = moving ? Math.sin(ph) * 0.1 : 0, up = moving ? Math.max(0, Math.cos(ph)) * 0.06 : 0;
      const r = L.root, s = L.side, spread = 0.36 - Math.abs(L.k - 1) * 0.04;
      const c = collapse;
      // normal stance blended with a splayed, flat-on-the-table pose
      const knee = [r[0] + swing * 0.6 + (L.k - 1) * -0.12, r[1] + 0.14 * (1 - c) + 0.03 * c, r[2] + s * (0.22 + 0.12 * c)];
      const ankle = [r[0] + swing + (L.k - 1) * (-0.2 + 0.1 * c), (-0.38 + up) * (1 - c) + -0.2 * c, r[2] + s * (spread + 0.22 * c)];
      const foot = [ankle[0] + 0.12 + 0.06 * c, (-0.4 + up * 0.5) * (1 - c) + -0.2 * c, ankle[2] + s * (0.04 + 0.08 * c)];
      place(L.upper, r, knee, 0.017); place(L.lower, knee, ankle, 0.011); place(L.foot, ankle, foot, 0.006);
      L.knee.position.set(knee[0], knee[1], knee[2]);
    }
  }

  return { group: fly, parts: flyParts, animate: animateFly };
  }

  // ---------------------------------------------------------------- CNS
  // Fixed anatomical projections drawn straight into pixel buffers: a dim
  // density silhouette of every positioned soma, the neurons that fired in
  // the current trial in bright colour, and the readout cells as markers.
  const CNS = { n: 0, cells: null, cur: null, target: null, views: [], ok: null, schematic: true, big: false, windowMs: 500 };
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
    for (const [kind, idxs] of [["left", atlas.cells.left], ["right", atlas.cells.right], ["gate", atlas.cells.gate], ["reward", atlas.cells.reward || []]]) for (const i of idxs) CNS.hi.push({ i, kind });
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
    $("#brain-stats").textContent = counts ? `${firing.toLocaleString()} of ${CNS.n.toLocaleString()} cells fired · max ${max} spikes / ${CNS.windowMs || 500} ms` : "no trial loaded";
  }
  const COLORS = { fire: [200, 236, 70], left: [56, 189, 248], right: [56, 189, 248], gate: [251, 191, 36], reward: [232, 121, 249] };
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
  window.FLYLIB = { createStage, label, buildFly, CNS, loadAtlas, setActivity, animateCNS, VIEW_W, VIEW_H };
})();
