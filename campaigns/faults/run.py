"""Fault-injection campaign for TT #777: simulate every fault, score against the golden model.

Writes results/faults_tt777.csv, one row per fault, with three checker levels:
  L0  design's own test   : DONE asserted                         (what upstream test checks)
  L1  DONE + FAIL flag    : FAIL equals golden prediction
  L2  full scoreboard     : FAIL, every fail address, repair table all equal golden prediction
Usage: python campaigns/faults/run.py [--jobs 8]
"""
import argparse
import csv
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tb"))
from refmodel import MARCH_C_MINUS, MARCH_TT777, Fault, run_march  # noqa: E402

D, W, NREP = 32, 8, 2
SRC = ROOT / "duts" / "tt777" / "src"
VVP = ROOT / "build" / "tt777_fault.vvp"


def build():
    VVP.parent.mkdir(exist_ok=True)
    files = [SRC / f for f in ("memory.v", "mbisr_controller.v", "mbist_marchc_controller.v", "top.v")]
    subprocess.run(["iverilog", "-g2012", "-o", str(VVP), *map(str, files),
                    str(ROOT / "tb" / "tt777" / "tb_tt777_fault.v")], check=True)


def fault_list():
    out = []
    for a in range(D):
        for b in range(W):
            for v in (0, 1):
                out.append(Fault("SAF", a, b, v))
                out.append(Fault("TF", a, b, v))
    # Coupling (idempotent): physically adjacent aggressors (row above/below, neighbouring bit)
    for a in range(D):
        for b in range(W):
            aggs = [(a - 1, b), (a + 1, b), (a, b ^ 1)]
            for aa, ab in aggs:
                if 0 <= aa < D:
                    for t in (0, 1):
                        for v in (0, 1):
                            out.append(Fault("CF", a, b, v, aa, ab, t))
    return out


def simulate(f):
    args = ["vvp", "-n", str(VVP)]
    code = {"SAF": 0, "TF": 1, "CF": 2}[f.kind]
    args += [f"+FT={code}", f"+A={f.a}", f"+B={f.b}", f"+V={f.v}"]
    if f.kind == "CF":
        args += [f"+AA={f.aa}", f"+AB={f.ab}", f"+T={f.t}"]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    obs = {"fail_addrs": [], "repair": [], "done": 0, "fail": 0}
    for line in out.splitlines():
        p = line.split()
        if not p or p[0] != "RESULT":
            continue
        if p[1] == "failaddr":
            obs["fail_addrs"].append(int(p[2]))
        elif p[1] == "done":
            obs["done"], obs["fail"] = int(p[2]), int(p[4])
        elif p[1] == "repair" and p[3] == "1":
            obs["repair"].append(int(p[4]))
    return obs


def score(f):
    exp = run_march(MARCH_TT777, D, W, f, NREP)
    full = run_march(MARCH_C_MINUS, D, W, f, NREP)
    obs = simulate(f)
    flag_ok = bool(obs["fail"]) == exp["fail"]
    addr_ok = obs["fail_addrs"] == exp["fail_addrs"]
    rep_ok = sorted(obs["repair"]) == sorted(exp["repair"])
    row = f.as_dict()
    row.update({
        "exp_fail": int(exp["fail"]), "dut_fail": obs["fail"], "dut_done": obs["done"],
        "exp_addrs": " ".join(map(str, exp["fail_addrs"])),
        "dut_addrs": " ".join(map(str, obs["fail_addrs"])),
        "exp_repair": " ".join(map(str, exp["repair"])),
        "dut_repair": " ".join(map(str, obs["repair"])),
        "flag_ok": int(flag_ok), "addr_ok": int(addr_ok), "repair_ok": int(rep_ok),
        "bug_L0": int(not obs["done"]),
        "bug_L1": int(not obs["done"] or not flag_ok),
        "bug_L2": int(not obs["done"] or not (flag_ok and addr_ok and rep_ok)),
        "full_marchc_detects": int(full["fail"]),
    })
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "results" / "faults_tt777.csv"))
    args = ap.parse_args()
    build()
    faults = fault_list()
    with ThreadPoolExecutor(args.jobs) as ex:
        rows = list(ex.map(score, faults))
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} faults -> {args.out}")


if __name__ == "__main__":
    random.seed(1)
    main()
