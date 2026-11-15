"""Chip-level campaign on mbist_ctrl: all eight MBIST/BISR instances + glbl_cfg (tb/mbist_ctrl/tb_mbist_sys.v).

Each run spreads up to 16 SAF/TF faults over the user words of several memories at once, runs all
eight BISTs in parallel, reads the two BIST status registers, the eight repair tables, and then checks
every memory over its functional bus through the repair remap.

Golden (per instance, n = distinct faulty user words; spares fault-free):
  status byte {cnt[3:0], 0, correct, error, done}:
    n = 0      -> 0x01 ; repair table empty ; functional bad words 0
    1 <= n <= 4 -> (n << 4) | 0x05 ; repair table = the n words ; functional bad words 0
    n > 4      -> done = 1, error = 1 ; functional bad words = n - 4 (only 4 spares)
Writes results/system.csv.  Usage: python campaigns/system/run_sys.py [--runs 40] [--jobs 3]
"""
import argparse
import csv
import random
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VVP = ROOT / "build" / "sys.vvp"
USER_WORDS = [508] * 4 + [252] * 4


def build():
    d = "duts/mbist_ctrl/verilog/rtl"
    r = d + "/mbist"
    core = sorted(str(p.relative_to(ROOT)) for p in (ROOT / r / "src/core").glob("*.sv"))
    subprocess.run(["iverilog", "-g2005-sv", "-o", str(VVP), "-I", r + "/include", "-DFUNCTIONAL", "-DSIM",
                    "tb/mbist_ctrl/timescale.v", r + "/src/top/mbist_top1.sv", r + "/src/top/mbist_top2.sv", *core,
                    d + "/lib/reset_sync.sv", d + "/lib/registers.v", d + "/lib/ser_inf_32b.sv",
                    d + "/glbl/src/glbl_cfg.sv", "tb/mbist_ctrl/stubs.v",
                    "tb/mbist_ctrl/sky130_sram_2kbyte_1rw1r_32x512_8_icarus.v",
                    "tb/mbist_ctrl/sky130_sram_1kbyte_1rw1r_32x256_8_icarus.v",
                    "tb/mbist_ctrl/tb_mbist_sys.v", "-s", "tb_mbist_sys"], cwd=ROOT, check=True,
                   capture_output=True)


def gen(seed):
    rnd = random.Random(seed)
    faults, budget = [], 16
    for inst in rnd.sample(range(8), rnd.randint(1, 8)):
        n = rnd.choice([1, 1, 2, 3, 4, 4, 5, 6])
        words = rnd.sample(range(USER_WORDS[inst]), n)
        for w in words:
            k = 1 + (rnd.random() < 0.2)  # sometimes two faulty bits in one word
            for _ in range(k):
                if budget == 0:
                    break
                faults.append((inst, rnd.randint(0, 1), w, rnd.randrange(32), rnd.randint(0, 1)))
                budget -= 1
    return faults


def sim(faults):
    args = ["vvp", "-n", str(VVP), f"+NF={len(faults)}"]
    for i, (g, k, a, b, v) in enumerate(faults):
        args += [f"+FI{i}={g}", f"+FK{i}={k}", f"+FA{i}={a}", f"+FB{i}={b}", f"+FV{i}={v}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=1200).stdout
    o = {"rep": defaultdict(list), "repcnt": {}, "func": {}}
    for line in out.splitlines():
        p = line.split()
        if p[:2] == ["RESULT", "status1"]:
            o["s1"], o["s2"], o["cycles"] = int(p[2], 16), int(p[4], 16), int(p[6])
        elif p[:2] == ["RESULT", "inst"] and p[3] == "repcnt":
            o["repcnt"][int(p[2])] = int(p[4]) if p[4] != "x" else 0
        elif p[:2] == ["RESULT", "inst"] and p[3] == "repair" and p[5] != "x":
            o["rep"][int(p[2])].append(int(p[5]))
        elif p[:2] == ["RESULT", "inst"] and p[3] == "func_bad":
            o["func"][int(p[2])] = int(p[4])
    return o


def score(run_id, faults):
    o = sim(faults)
    rows = []
    for g in range(8):
        words = sorted({a for (i, _, a, _, _) in faults if i == g})
        n = len(words)
        byte = ((o["s1"] if g < 4 else o["s2"]) >> (8 * (g % 4))) & 0xFF
        rep = sorted(o["rep"][g][: o["repcnt"].get(g, 0)])
        if n <= 4:
            exp_byte = 0x01 if n == 0 else (n << 4) | 0x05
            status_ok = byte == exp_byte
            repair_ok = rep == words
            func_ok = o["func"].get(g) == 0
        else:
            status_ok = (byte & 0x03) == 0x03
            repair_ok = True  # golden does not fix which 4 of the n words are repaired
            func_ok = o["func"].get(g) == n - 4
        rows.append({"run": run_id, "inst": g, "words": n, "faults": sum(f[0] == g for f in faults),
                     "status_byte": f"{byte:02x}", "repair": " ".join(map(str, rep)),
                     "exp_repair": " ".join(map(str, words)), "func_bad": o["func"].get(g, -1),
                     "status_ok": int(status_ok), "repair_ok": int(repair_ok), "func_ok": int(func_ok),
                     "cycles": o.get("cycles", -1)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    build()
    out = ROOT / "results" / "system.csv"
    with open(out, "w", newline="") as fh, ThreadPoolExecutor(args.jobs) as ex:
        w = None
        for rows in ex.map(lambda s: score(s, gen(1000 + s)), range(args.runs)):
            if w is None:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
            w.writerows(rows)
            fh.flush()
            bad = [r for r in rows if not (r["status_ok"] and r["repair_ok"] and r["func_ok"])]
            print(f"run {rows[0]['run']}: {sum(r['words'] for r in rows)} faulty words, mismatches {len(bad)}",
                  flush=True)
    print("->", out)


if __name__ == "__main__":
    main()
