"""fig_alg_rtl.pdf: RTL coverage of each March algorithm loaded into Design B, per fault class,
plus test length; appends RTL-vs-golden agreement and Wilson intervals to results/stats_alg_rtl.txt."""
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
plt.style.use(ROOT / "figs" / "style.mplstyle")
BLUES = LinearSegmentedColormap.from_list("b", ["#F4F8FB", "#9EC5E2", "#0072B2", "#003F63"])


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


R = list(csv.DictReader(open(ROOT / "results" / "algorithms_rtl.csv")))
algs = list(dict.fromkeys(r["algorithm"] for r in R))
cls = ["SAF", "TF", "CF inter-word", "CF intra-word"]
cnt = defaultdict(lambda: [0, 0])
cyc = defaultdict(list)
for r in R:
    cnt[(r["algorithm"], r["class"])][0] += int(r["dut_detect"])
    cnt[(r["algorithm"], r["class"])][1] += 1
    cyc[r["algorithm"]].append(int(r["cycles"]))
H = np.array([[100 * cnt[(a, c)][0] / cnt[(a, c)][1] for c in cls] for a in algs])
kc = {a: round(np.median(cyc[a]) / 1000) for a in algs}

fig, ax = plt.subplots(figsize=(3.5, 1.95))
ax.imshow(H, aspect="auto", cmap=BLUES, vmin=0, vmax=100)
ax.set_xticks(range(len(cls)))
ax.set_xticklabels([c.replace(" ", "\n", 1) for c in cls], fontsize=6)
ax.set_yticks(range(len(algs)))
ax.set_yticklabels([f"{a} ({kc[a]}k cyc.)" for a in algs], fontsize=6)
ax.xaxis.tick_top()
ax.grid(False)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        ax.text(j, i, f"{H[i, j]:.0f}%", ha="center", va="center", fontsize=6,
                color="white" if H[i, j] > 60 else "#1B1B1B")
plt.savefig(ROOT / "figs" / "fig_alg_rtl.pdf")
plt.savefig(ROOT / "figs" / "fig_alg_rtl.png", dpi=200)

n, m = len(R), sum(r["match_golden"] == "1" for r in R)
out = [f"RTL runs {n}, match golden {m}, mismatches {n - m}, upper 95% bound {100 * wilson(n - m, n)[2]:.2f}%"]
for a in algs:
    k = sum(int(r["dut_detect"]) for r in R if r["algorithm"] == a)
    t = sum(r["algorithm"] == a for r in R)
    p, l, h = wilson(k, t)
    out.append(f"{a}: detect {k}/{t} = {100*p:.1f}% [{100*l:.1f}-{100*h:.1f}], median cycles {np.median(cyc[a]):.0f}")
for c in cls:
    for a in algs:
        k, t = cnt[(a, c)]
        out.append(f"  {c} / {a}: {k}/{t}")
(ROOT / "results" / "stats_alg_rtl.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
