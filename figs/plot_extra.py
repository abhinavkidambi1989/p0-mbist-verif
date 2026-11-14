"""Extra paper figures + statistics.

fig_escape_map.pdf : Design A escapes per address and fault class (heatmap).
fig_algorithms.pdf : golden-model coverage per March algorithm and fault class (heatmap).
fig_mutants.pdf    : seeded-bug kill rate per checker level, both designs, Wilson 95% CI.
results/stats.txt  : Wilson 95% intervals for every rate quoted in the paper.
"""
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
plt.style.use(ROOT / "figs" / "style.mplstyle")
BLUES = LinearSegmentedColormap.from_list("b", ["#F4F8FB", "#9EC5E2", "#0072B2", "#003F63"])


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def rd(name):
    p = ROOT / "results" / name
    return list(csv.DictReader(open(p))) if p.exists() else []


stats = []
A = rd("faults_tt777.csv")
B = rd("faults_mbist_ctrl.csv")

# ---------------- escape map (Design A) ----------------
classes = [("SAF", lambda r: r["kind"] == "SAF"), ("TF", lambda r: r["kind"] == "TF"),
           ("CF inter", lambda r: r["kind"] == "CF" and r["aa"] != r["a"]),
           ("CF intra", lambda r: r["kind"] == "CF" and r["aa"] == r["a"])]
M = np.zeros((len(classes), 32))
for i, (_, f) in enumerate(classes):
    for r in A:
        if f(r) and r["exp_fail"] == "1" and r["dut_fail"] == "0":
            M[i, int(r["a"])] += 1
fig, ax = plt.subplots(figsize=(3.5, 1.25))
im = ax.imshow(M, aspect="auto", cmap=BLUES, vmin=0, vmax=max(1, M.max()))
ax.set_yticks(range(len(classes)))
ax.set_yticklabels([c for c, _ in classes], fontsize=6.5)
ax.set_xticks([0, 8, 16, 24, 31])
ax.set_xlabel("Faulty cell address (victim for CF)")
ax.grid(False)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if M[i, j]:
            ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center", fontsize=5,
                    color="white" if M[i, j] > M.max() / 2 else "#1B1B1B")
cb = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.04)
cb.ax.tick_params(labelsize=5.5)
cb.set_label("escapes", fontsize=6)
plt.savefig(ROOT / "figs" / "fig_escape_map.pdf")
plt.savefig(ROOT / "figs" / "fig_escape_map.png", dpi=200)

# ---------------- algorithm coverage heatmap ----------------
AL = rd("algorithms.csv")
if AL:
    algs = list(dict.fromkeys(r["algorithm"] for r in AL))
    cls = list(dict.fromkeys(r["class"] for r in AL))
    ops = {r["algorithm"]: r["ops_per_word"] for r in AL}
    H = np.array([[100 * int(r["detected"]) / int(r["total"]) for r in AL if r["algorithm"] == a] for a in algs])
    fig, ax = plt.subplots(figsize=(3.5, 1.75))
    ax.imshow(H, aspect="auto", cmap=BLUES, vmin=0, vmax=100)
    ax.set_xticks(range(len(cls)))
    ax.set_xticklabels([c.replace(" ", "\n", 1) for c in cls], fontsize=6)
    ax.set_yticks(range(len(algs)))
    ax.set_yticklabels([f"{a} ({ops[a]}N)" for a in algs], fontsize=6)
    ax.grid(False)
    ax.xaxis.tick_top()
    for i in range(H.shape[0]):
        for j in range(H.shape[1]):
            ax.text(j, i, f"{H[i, j]:.0f}%", ha="center", va="center", fontsize=6,
                    color="white" if H[i, j] > 60 else "#1B1B1B")
    plt.savefig(ROOT / "figs" / "fig_algorithms.pdf")
    plt.savefig(ROOT / "figs" / "fig_algorithms.png", dpi=200)

# ---------------- mutants ----------------
MA, MB = rd("mutants_tt777.csv"), rd("mutants_mbist_ctrl.csv")
if MA:
    levels = [("L0", "killed_L0"), ("L1", "killed_L1"), ("L1c", "killed_L1c"), ("L2", "killed_L2")]
    designs = [("Design A (TT #777)", MA, "#0072B2")] + ([("Design B (mbist_ctrl)", MB, "#E69F00")] if MB else [])
    fig, ax = plt.subplots(figsize=(3.5, 1.9))
    w = 0.38
    for d, (name, rows, col) in enumerate(designs):
        xs, ys, lo, hi = [], [], [], []
        for i, (lab, key) in enumerate(levels):
            if name.startswith("Design A") and lab == "L1c":
                continue
            k = sum(int(r[key]) for r in rows)
            p, l, h = wilson(k, len(rows))
            xs.append(i + (d - 0.5) * w * (1 if MB else 0))
            ys.append(100 * p)
            lo.append(100 * (p - l))
            hi.append(100 * (h - p))
            stats.append(f"mutants {name} {lab}: {k}/{len(rows)} = {100*p:.1f}% [95% CI {100*l:.1f}-{100*h:.1f}]")
        ax.bar(xs, ys, width=w * 0.92, color=col, label=name, yerr=[lo, hi],
               error_kw={"elinewidth": 0.6, "capsize": 1.5, "ecolor": "#555555"})
        for x, y in zip(xs, ys):
            ax.text(x, 2, f"{y:.0f}", ha="center", va="bottom", fontsize=5.5, color="white")
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels(["L0\nDONE", "L1\n+ flag", "L1c\n+ count", "L2\n+ addr./repair"], fontsize=6)
    ax.set_ylabel("Seeded bugs killed (%)")
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=6)
    plt.savefig(ROOT / "figs" / "fig_mutants.pdf")
    plt.savefig(ROOT / "figs" / "fig_mutants.png", dpi=200)

# ---------------- stats for the text ----------------
det = [r for r in A if r["exp_fail"] == "1"]
dd = [r for r in A if r["exp_fail"] == "1" and r["dut_fail"] == "1"]
for label, k, n in [
    ("A escapes / detectable", sum(r["dut_fail"] == "0" for r in det), len(det)),
    ("A faulty cell in repair table / detected", sum(r["a"] in r["dut_repair"].split() for r in dd), len(dd)),
    ("A L1 exposes / detectable", sum(int(r["bug_L1"]) for r in det), len(det)),
    ("A L2 exposes / detectable", sum(int(r["bug_L2"]) for r in det), len(det)),
    ("B L2 false alarms / non-spare runs", sum(int(r["bug_L2"]) for r in B if r["spare_fault"] == "0"),
     sum(r["spare_fault"] == "0" for r in B)),
]:
    p, l, h = wilson(k, n)
    stats.append(f"{label}: {k}/{n} = {100*p:.2f}% [95% CI {100*l:.2f}-{100*h:.2f}]")
(ROOT / "results" / "stats.txt").write_text("\n".join(stats) + "\n")
print("\n".join(stats))
