"""Render a window of a VCD file as a paper-style digital waveform (PDF + PNG).

Usage: python figs/plot_wave.py <vcd> <t_start_ns> <t_end_ns> <out_basename> "<title>" [mark_ns ...]
Signals shown are the w_* probes in tb_tt777.v. No external VCD library needed.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
plt.style.use(ROOT / "figs" / "style.mplstyle")

STATE = {0: "IDLE", 1: "W0", 2: "W0F", 3: "↑r0w1", 4: "R0W1F", 5: "↓r1w0", 6: "R1W0F",
         7: "↑r0", 8: "DONE"}
SHOW = [  # (vcd name, label, kind)
    ("clk", "clk", "bit"),
    ("w_state", "march element", "state"),
    ("w_mem_addr", "mem_addr", "dec"),
    ("w_mem_we", "mem_we", "bit"),
    ("w_rdata", "mem_rdata", "hex"),
    ("w_read_addr", "read_addr", "dec"),
    ("w_fail_v", "fail_valid", "bit"),
    ("w_fail_addr", "fail_addr", "dec"),
    ("w_rv0", "repair[0].valid", "bit"),
    ("w_rt0", "repair[0].addr", "dec"),
    ("w_rv1", "repair[1].valid", "bit"),
    ("w_rt1", "repair[1].addr", "dec"),
    ("done", "DONE", "bit"),
    ("fail", "FAIL", "bit"),
]


def parse_vcd(path):
    ids, traces, t, scale = {}, {}, 0, 1.0
    in_tb = False
    with open(path) as f:
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if tok[0] == "$timescale":
                ts = " ".join(tok[1:]).replace("$end", "").strip() or next(f).strip()
                scale = {"1ps": 1e-3, "1ns": 1.0}.get(ts.replace(" ", ""), 1.0)
            elif tok[0] == "$scope":
                in_tb = tok[2] in ("tb_tt777",)
            elif tok[0] == "$var" and in_tb:
                ids.setdefault(tok[3], []).append(tok[4])
            elif tok[0].startswith("#"):
                t = int(tok[0][1:]) * scale
            elif tok[0][0] in "01xz" and len(tok) == 1:
                for n in ids.get(tok[0][1:], []):
                    traces.setdefault(n, []).append((t, tok[0][0]))
            elif tok[0][0] == "b" and len(tok) == 2:
                for n in ids.get(tok[1], []):
                    traces.setdefault(n, []).append((t, tok[0][1:]))
    return traces


def value_at(trace, t):
    v = None
    for tt, vv in trace:
        if tt > t:
            break
        v = vv
    return v


def fmt(v, kind):
    if v is None or any(c in v for c in "xz"):
        return "x"
    n = int(v, 2)
    if kind == "state":
        return STATE.get(n, str(n))
    if kind == "hex":
        return f"{n:02X}"
    return str(n)


def main():
    vcd, t0, t1, out, title = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
    marks = [float(m) for m in sys.argv[6:]]
    tr = parse_vcd(vcd)
    rows = [s for s in SHOW if s[0] in tr]
    fig, ax = plt.subplots(figsize=(7.16, 0.28 * len(rows) + 0.6))
    for i, (name, label, kind) in enumerate(rows):
        y = len(rows) - 1 - i
        pts = [(t0, value_at(tr[name], t0))] + [(t, v) for t, v in tr[name] if t0 < t < t1] + [(t1, None)]
        for (ta, va), (tb, _) in zip(pts[:-1], pts[1:]):
            if kind == "bit":
                h = 0.7 if va == "1" else 0.0
                ax.plot([ta, tb], [y + h, y + h], color="#0072B2", lw=0.9)
                ax.plot([tb, tb], [y, y + 0.7], color="#0072B2", lw=0.4, alpha=0.6)
            else:
                ax.fill_between([ta + 0.4, tb - 0.4], y + 0.05, y + 0.65, color="#E8F1F8", lw=0)
                ax.plot([ta + 0.4, tb - 0.4], [y + 0.05, y + 0.05], color="#0072B2", lw=0.6)
                ax.plot([ta + 0.4, tb - 0.4], [y + 0.65, y + 0.65], color="#0072B2", lw=0.6)
                if tb - ta >= 6:
                    ax.text((ta + tb) / 2, y + 0.35, fmt(va, kind), ha="center", va="center", fontsize=6)
        ax.text(t0 - (t1 - t0) * 0.01, y + 0.35, label, ha="right", va="center", fontsize=7)
    for m in marks:
        ax.axvline(m, color="#CC79A7", lw=1.0, ls="--")
    ax.set_xlim(t0, t1)
    ax.set_ylim(-0.3, len(rows))
    ax.set_yticks([])
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("time (ns)")
    ax.set_title(title, fontsize=8, loc="left")
    plt.savefig(ROOT / f"{out}.pdf")
    plt.savefig(ROOT / f"{out}.png", dpi=200)
    print("wrote", out + ".pdf/.png")


if __name__ == "__main__":
    main()
