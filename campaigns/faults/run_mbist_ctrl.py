"""Fault campaign for mbist_ctrl (second DUT): simulate, score against the golden repair model.

Golden model (repair level). The design's algorithm (8 data backgrounds incl. all-0/all-1, 5 March
stimuli, read-after-write in both address directions) detects every single-cell SAF and TF, so for
a set W of distinct faulty user words (0x000-0x1FB) a correct MBIST/BISR must report:
  |W| <= 4 : DONE=1, ERROR=0, CORRECT=(|W|>0), error count = |W|, repair table = W (as a set)
  |W| >  4 : DONE=1, ERROR=1 (unrepairable)
Faults in spare words (0x1FC-0x1FF) are recorded separately (spec does not define the outcome).
Checker levels as for TT #777: L0 DONE, L1 DONE+ERROR vs golden, L2 + count + repair table.
Writes results/faults_mbist_ctrl.csv.
"""
import argparse
import csv
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VVP = ROOT / "build" / "mc.vvp"
NWORDS, NREP, SPARE0 = 508, 4, 0x1FC


def simulate(faults):
    args = ["vvp", "-n", str(VVP), f"+N={len(faults)}"]
    for i, (k, a, b, v) in enumerate(faults):
        args += [f"+K{i}={k}", f"+A{i}={a}", f"+B{i}={b}", f"+V{i}={v}"]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    obs = {"repair": []}
    for line in out.splitlines():
        p = line.split()
        if p[:2] == ["RESULT", "done"]:
            obs.update(done=int(p[2]), error=int(p[4]), correct=int(p[6]), errcnt=int(p[8]), cycles=int(p[10]))
        elif p[:2] == ["RESULT", "repcnt"]:
            obs["repcnt"] = int(p[2])
        elif p[:2] == ["RESULT", "repair"] and p[3] != "x":
            obs["repair"].append(int(p[3]))
    obs["repair"] = obs["repair"][: obs.get("repcnt", 0)]
    return obs


def score(case):
    cls, faults = case
    words = sorted({a for _, a, _, _ in faults if a < SPARE0})
    spare = any(a >= SPARE0 for _, a, _, _ in faults)
    n = len(words)
    exp = {"error": int(n > NREP), "correct": int(0 < n <= NREP), "errcnt": n if n <= NREP else None,
           "repair": words if n <= NREP else None}
    obs = simulate(faults)
    flag_ok = obs["error"] == exp["error"]
    full_ok = flag_ok and (n > NREP or (obs["correct"] == exp["correct"] and obs["errcnt"] == exp["errcnt"]
                                        and sorted(obs["repair"]) == exp["repair"]))
    return {
        "class": cls, "nfaults": len(faults), "nwords": n, "spare_fault": int(spare),
        "faults": ";".join(f"{k},{a},{b},{v}" for k, a, b, v in faults),
        "exp_error": exp["error"], "dut_done": obs["done"], "dut_error": obs["error"],
        "dut_correct": obs["correct"], "dut_errcnt": obs["errcnt"],
        "dut_repair": " ".join(map(str, obs["repair"])), "exp_repair": " ".join(map(str, words)),
        "cycles": obs["cycles"],
        "bug_L0": int(not obs["done"]),
        "bug_L1": int(not spare and (not obs["done"] or not flag_ok)),
        "bug_L2": int(not spare and (not obs["done"] or not full_ok)),
    }


def cases():
    rnd = random.Random(2026)
    out = []
    for a in range(NWORDS):
        b = a % 32
        for v in (0, 1):
            out.append(("SAF", [(0, a, b, v)]))
            out.append(("TF", [(1, a, b, v)]))
    for nw in (2, 3, 4, 5, 6):
        for _ in range(30):
            ws = rnd.sample(range(NWORDS), nw)
            out.append((f"multi-{nw}", [(rnd.randint(0, 1), w, rnd.randrange(32), rnd.randint(0, 1)) for w in ws]))
    for s in range(4):  # faulty spare, alone and combined with user faults that consume spares up to it
        out.append(("spare", [(0, SPARE0 + s, 0, 0)]))
        for nw in range(1, 5):
            ws = rnd.sample(range(NWORDS), nw)
            out.append(("spare", [(0, SPARE0 + s, 0, 0)] + [(0, w, 3, 1) for w in ws]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--out", default=str(ROOT / "results" / "faults_mbist_ctrl.csv"))
    args = ap.parse_args()
    subprocess.run(["bash", str(ROOT / "tb" / "mbist_ctrl" / "build.sh")], check=True)
    cs = cases()
    with ThreadPoolExecutor(args.jobs) as ex:
        rows = list(ex.map(score, cs))
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} cases -> {args.out}")


if __name__ == "__main__":
    main()
