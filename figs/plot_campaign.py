"""Figures from results/faults_tt777.csv.

fig_detection.pdf : fault detection (%) per fault class - full March C- (theory),
                    implemented 4-element test (golden model), DUT FAIL flag.
fig_checkers.pdf  : % of detectable faults whose run exposes a design bug, per checker level.
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
plt.style.use(ROOT / "figs" / "style.mplstyle")
rows = list(csv.DictReader(open(ROOT / "results" / "faults_tt777.csv")))


def pct(rs, key):
    return 100.0 * sum(int(r[key]) for r in rs) / len(rs)


classes = [
    ("SAF", [r for r in rows if r["kind"] == "SAF"]),
    ("TF", [r for r in rows if r["kind"] == "TF"]),
    ("CF\ninter-word", [r for r in rows if r["kind"] == "CF" and r["aa"] != r["a"]]),
    ("CF\nintra-word", [r for r in rows if r["kind"] == "CF" and r["aa"] == r["a"]]),
]
series = [("Full March C- (golden)", "full_marchc_detects", "#0072B2"),
          ("Implemented 4-element test (golden)", "exp_fail", "#009E73"),
          ("DUT FAIL flag (simulated)", "dut_fail", "#E69F00")]

# ---------- Fig: detection per class ----------
fig, ax = plt.subplots(figsize=(3.5, 2.45))
w = 0.27
for i, (label, key, col) in enumerate(series):
    xs = [j + (i - 1) * (w + 0.02) for j in range(len(classes))]
    ys = [pct(rs, key) for _, rs in classes]
    ax.bar(xs, ys, width=w, color=col, label=label, edgecolor="white", linewidth=0.6)
    for x, y in zip(xs, ys):
        ax.text(x, y + 1.5, f"{y:.0f}", ha="center", va="bottom", fontsize=5, rotation=90)
ax.set_xticks(range(len(classes)))
ax.set_xticklabels([f"{n}\n(n={len(rs)})" for n, rs in classes], fontsize=6)
ax.set_ylabel("Faults detected (%)")
ax.set_ylim(0, 112)
ax.set_yticks([0, 25, 50, 75, 100])
ax.grid(axis="x", visible=False)
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.25), ncol=1, frameon=False, fontsize=6)
plt.savefig(ROOT / "figs" / "fig_detection.pdf")
plt.savefig(ROOT / "figs" / "fig_detection.png", dpi=200)

# ---------- Fig: checker levels ----------
det = [r for r in rows if r["exp_fail"] == "1"]
levels = [("L0: DONE only", "bug_L0"),
          ("L1: DONE + FAIL\nvs. golden", "bug_L1"),
          ("L2: full scoreboard\n(+ fail addr., repair)", "bug_L2")]
mc_path = ROOT / "results" / "faults_mbist_ctrl.csv"
mc = [r for r in csv.DictReader(open(mc_path)) if r["spare_fault"] == "0"] if mc_path.exists() else []
designs = [("Design A (TT #777)", det, "#0072B2")] + ([("Design B (mbist_ctrl)", mc, "#E69F00")] if mc else [])
fig, ax = plt.subplots(figsize=(3.5, 1.9 if mc else 1.45))
h = 0.36 if mc else 0.55
base = list(range(len(levels)))[::-1]
for d, (name, rs, col) in enumerate(designs):
    off = (0.5 - d) * h if mc else 0
    vals = [pct(rs, k) for _, k in levels]
    cnts = [sum(int(r[k]) for r in rs) for _, k in levels]
    ys = [y + off for y in base]
    ax.barh(ys, vals, height=h * 0.92, color=col, label=name)
    for y, v, c in zip(ys, vals, cnts):
        ax.text(v + 1.5, y, f"{v:.1f}%  ({c}/{len(rs)})", va="center", fontsize=6)
ax.set_yticks(base)
ax.set_yticklabels([l for l, _ in levels], fontsize=6.5)
ax.set_xlim(0, 140)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("Detectable fault runs exposing a design bug (%)")
ax.grid(axis="y", visible=False)
if mc:
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.52), frameon=False, fontsize=6)
plt.savefig(ROOT / "figs" / "fig_checkers.pdf")
plt.savefig(ROOT / "figs" / "fig_checkers.png", dpi=200)
print("wrote figs/fig_detection.* and figs/fig_checkers.*")
