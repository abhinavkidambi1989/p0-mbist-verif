"""Scaling study on Design B (mbist_ctrl): the same controller RTL built for memories of
2^AW words (AW = 9 .. 14, i.e. 512 to 16,384 words x 32 bits; 4 spares, user words 0 .. 2^AW-5,
as in the chip's own 512-word configuration). For each size: one fault-free run, single SAF/TF/CF
faults at random words, a 3-word repairable set and a 5-word unrepairable set. Every run is scored
against the golden model at the repair level, and simulation and golden-model run times are logged.
Writes results/scaling.csv.  Usage: python campaigns/scaling/run_scaling.py [--jobs 2]
"""
import argparse
import csv
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tb"))
sys.path.insert(0, str(ROOT / "campaigns" / "algorithms"))
import refmodel as rm  # noqa: E402
import run_rtl as R  # noqa: E402  (simulate(), DEFAULT_BG)

SIZES = [9, 10, 11, 12, 13, 14]


def sample(nw, rnd):
    t = [("fault-free", [])]
    for _ in range(3):
        t.append(("SAF", [rm.Fault("SAF", rnd.randrange(nw), rnd.randrange(32), rnd.randint(0, 1))]))
    for _ in range(3):
        t.append(("TF", [rm.Fault("TF", rnd.randrange(nw), rnd.randrange(32), rnd.randint(0, 1))]))
    for _ in range(2):
        a, b = rnd.randrange(1, nw - 1), rnd.randrange(32)
        t.append(("CF inter-word", [rm.Fault("CF", a, b, rnd.randint(0, 1), a + 1, b, rnd.randint(0, 1))]))
    t.append(("3 words", [rm.Fault("SAF", w, rnd.randrange(32), rnd.randint(0, 1)) for w in rnd.sample(range(nw), 3)]))
    t.append(("5 words", [rm.Fault("SAF", w, rnd.randrange(32), rnd.randint(0, 1)) for w in rnd.sample(range(nw), 5)]))
    t.append(("boundary", [rm.Fault("SAF", 0, 0, 1), rm.Fault("SAF", nw - 1, 31, 0)]))
    return t


def sim_multi(vvp, faults):
    """Several SAF/TF faults via +N, or one CF via R.simulate."""
    if len(faults) == 1 or (faults and faults[0].kind == "CF"):
        return R.simulate(vvp, faults[0])
    args = ["vvp", "-n", str(vvp), "+MAXC=40000000", f"+N={len(faults)}"]
    for i, f in enumerate(faults):
        args += [f"+K{i}={0 if f.kind == 'SAF' else 1}", f"+A{i}={f.a}", f"+B{i}={f.b}", f"+V{i}={f.v}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=7200).stdout
    o = {"rep": []}
    for line in out.splitlines():
        p = line.split()
        if p[:2] == ["RESULT", "done"]:
            o.update(done=int(p[2]), error=int(p[4]), correct=int(p[6]), cnt=int(p[8]), cycles=int(p[10]))
        elif p[:2] == ["RESULT", "repcnt"]:
            o["repcnt"] = int(p[2]) if p[2] != "x" else 0
        elif p[:2] == ["RESULT", "repair"] and p[3] != "x":
            o["rep"].append(int(p[3]))
    o["rep"] = sorted(o["rep"][: o.get("repcnt", 0)])
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()
    out = ROOT / "results" / "scaling.csv"
    rows = []
    for aw in SIZES:
        nw = (1 << aw) - 4
        vvp = ROOT / "build" / "scale" / f"aw{aw}.vvp"
        subprocess.run(["bash", str(ROOT / "tb/mbist_ctrl/build.sh"), "-o", str(vvp), "-A", str(aw)], check=True)
        rnd = random.Random(aw)

        def work(item):
            cls, faults = item
            t0 = time.time()
            words = set()
            for f in faults:
                words |= set(rm.run_march(rm.MARCH_DESIGN_B, nw, 32, f, nrep=4, backgrounds=R.DEFAULT_BG)["fail_addrs"])
            words = sorted(words)
            tg = time.time() - t0
            t0 = time.time()
            o = sim_multi(vvp, faults)
            ts = time.time() - t0
            n = len(words)
            ok = (o.get("done") == 1 and o.get("error") == int(n > 4)
                  and (n > 4 or (o.get("correct") == int(n > 0) and o.get("cnt") == n and o["rep"] == words)))
            return {"aw": aw, "words": nw + 4, "class": cls, "golden_words": " ".join(map(str, words)),
                    "dut_repair": " ".join(map(str, o["rep"])), "cycles": o.get("cycles", -1),
                    "sim_s": round(ts, 2), "golden_s": round(tg, 2), "match_golden": int(ok)}

        with ThreadPoolExecutor(args.jobs) as ex:
            res = list(ex.map(work, sample(nw, rnd)))
        rows += res
        print(f"{nw + 4} words: {sum(r['match_golden'] for r in res)}/{len(res)} match, "
              f"cycles {res[0]['cycles']}, sim {res[0]['sim_s']} s", flush=True)
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    main()
