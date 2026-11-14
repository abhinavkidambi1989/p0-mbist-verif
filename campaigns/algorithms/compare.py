"""Golden-model fault coverage of March algorithms on a 32x8 memory (same fault list as Design A).

Writes results/algorithms.csv: one row per (algorithm, fault class) with detected / total.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tb"))
import refmodel as rm  # noqa: E402

D, W = 32, 8
ALGS = [
    ("MATS+", rm.MATS_PLUS, None, 5),
    ("March X (= Design A)", rm.MARCH_X, None, 6),
    ("March Y", rm.MARCH_Y, None, 8),
    ("March C-", rm.MARCH_C_MINUS, None, 10),
    ("March C-, 4 backgrounds", rm.MARCH_C_MINUS, [0x00, 0x55, 0x33, 0x0F], 40),
    ("Design B default", rm.MARCH_DESIGN_B, rm.DESIGN_B_BACKGROUNDS, 13 * 5),
]


def faults():
    out = {"SAF": [], "TF": [], "CF inter-word": [], "CF intra-word": []}
    for a in range(D):
        for b in range(W):
            for v in (0, 1):
                out["SAF"].append(rm.Fault("SAF", a, b, v))
                out["TF"].append(rm.Fault("TF", a, b, v))
            for aa, ab in [(a - 1, b), (a + 1, b), (a, b ^ 1)]:
                if 0 <= aa < D:
                    cls = "CF intra-word" if aa == a else "CF inter-word"
                    for t in (0, 1):
                        for v in (0, 1):
                            out[cls].append(rm.Fault("CF", a, b, v, aa, ab, t))
    return out


def main():
    fl = faults()
    rows = []
    for name, alg, bgs, ops_per_n in ALGS:
        for cls, fs in fl.items():
            det = sum(rm.run_march(alg, D, W, f, backgrounds=bgs)["fail"] for f in fs)
            rows.append({"algorithm": name, "ops_per_word": ops_per_n, "class": cls,
                         "detected": det, "total": len(fs)})
            print(f"{name:26s} {cls:14s} {det}/{len(fs)}", flush=True)
    with open(ROOT / "results" / "algorithms.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
