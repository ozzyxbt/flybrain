import time, numpy as np
t0 = time.time()
from flybrain.choice.backends import ConnectomeBrain
from flybrain.choice import manifest as mm, renderer
b = ConnectomeBrain("data/checkpoints/genesis.npz")
print("brain ready in %.1fs; checkpoint %s; cells L=%d R=%d gate=%d" % (time.time()-t0, b.checkpoint_sha256, len(b.cells["left"]), len(b.cells["right"]), len(b.cells["gate"])), flush=True)
m, _ = mm.load("manifests/gate-a-demo-v1.json")
a, c = mm.candidates(m, "name")[:2]
frame = renderer.render(m, "name", a, c, "standard")
for k in range(2):
    t1 = time.time(); counts, nt = b.evaluate(frame, 500); dt = time.time()-t1
    from flybrain.choice import decoder
    r = decoder.readout(counts, b.cells, 500)
    print("trial %d: %.1fs wall, total spikes %d, L=%s R=%s gate=%d raw=%s sha=%s" % (k, dt, int(counts.sum()), r["left_hz"], r["right_hz"], r["gate_spikes"], r["raw_side"], __import__("hashlib").sha256(counts.astype("<i4").tobytes()).hexdigest()[:16]), flush=True)
atlas = b.atlas(); pos = atlas["positions"]; ok = np.isfinite(pos).all(axis=1)
print("atlas positions ok: %d / %d" % (ok.sum(), len(pos)), flush=True)
