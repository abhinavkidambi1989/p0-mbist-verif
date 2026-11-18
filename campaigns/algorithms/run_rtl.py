"""Run several March algorithms on Design B's RTL by configuring its stimulus encoding.

Design B's March elements are compile-time parameters (BIST_STIMULUS_TYPE1..8 in mbist_def.svh);
its scan chain only selects among them. For each algorithm this script
  1. encodes each element as a 15-bit stimulus word
       [14] direction (1 = up), [13] reverse (keep address: next element runs the other way),
       [12] repeat (unused by the RTL), then 4 op slots, slot i = bits [3i+2:3i] = {write, read, invert},
       executed slot 3 first; empty slots are no-ops,
  2. writes a generated mbist_def.svh (elements, data backgrounds) and builds the RTL with it,
  3. runs a fixed fault sample (SAF, TF, inter- and intra-word idempotent CF),
  4. scores every run against the golden model running the same algorithm (repair level).
Writes results/algorithms_rtl.csv.  Usage: python campaigns/algorithms/run_rtl.py [--jobs 2]
"""
import argparse
import csv
import random
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tb"))
import refmodel as rm  # noqa: E402

INC = ROOT / "duts" / "mbist_ctrl" / "verilog" / "rtl" / "mbist" / "include"
BUILD = ROOT / "build" / "alg"
NW, W = 508, 32
U, Dn = "up", "down"

SOLID = [0x00000000, 0x00000000]  # controller needs >= 2 backgrounds: solid algorithms run twice
BG4 = [0x00000000, 0x55555555, 0x33333333, 0x0F0F0F0F]
DEFAULT_BG = [0x55555555, 0x33333333, 0x0F0F0F0F, 0x00FF00FF, 0x0000FFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0x00000000]
ALGS = [  # name, elements, backgrounds, shipped (no svh change)
    ("MATS+", [(U, ["w0"]), (U, ["r0", "w1"]), (Dn, ["r1", "w0"])], SOLID, False),
    ("March X", rm.MARCH_X, SOLID, False),
    ("March Y", rm.MARCH_Y, SOLID, False),
    ("March C-", rm.MARCH_C_MINUS, SOLID, False),
    ("March LR", [(U, ["w0"]), (Dn, ["r0", "w1"]), (U, ["r1", "w0", "r0", "w1"]), (U, ["r1", "w0"]),
                  (U, ["r0", "w1", "r1", "w0"]), (U, ["r0"])], SOLID, False),
    ("March C-, 4 bg.", rm.MARCH_C_MINUS, BG4, False),
    ("Default (shipped)", rm.MARCH_DESIGN_B, DEFAULT_BG, True),
]
UNENCODABLE = [("March SS", "elements with 5 operations; the controller holds at most 4")]


def encode(elements):
    words = []
    for i, (order, ops) in enumerate(elements):
        if len(ops) > 4:
            raise ValueError("more than 4 ops")
        nxt = elements[(i + 1) % len(elements)][0]
        up = order != Dn
        rev = int((nxt != Dn) != up)
        w = (int(up) << 14) | (rev << 13)
        for slot, op in zip((3, 2, 1, 0), ops):
            write, read, inv = int(op[0] == "w"), int(op[0] == "r"), int(op[1] == "1")
            w |= ((write << 2) | (read << 1) | inv) << (3 * slot)
        words.append(w)
    return words


def make_svh(name, elements, bgs):
    d = BUILD / name.replace(" ", "_").replace(",", "").replace(".", "").replace("+", "p").replace("-", "m")
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    words = encode(elements) + [0] * (8 - len(elements))
    pats = list(bgs) + [0] * (8 - len(bgs))
    lines = ["`ifndef BIST_DEFINE_SVH", "`define BIST_DEFINE_SVH", f"// generated for {name}",
             f"parameter BIST_DATA_PAT_SIZE  = {len(bgs)};"]
    lines += [f"parameter BIST_DATA_PAT_TYPE{i+1} = 64'h{p:016X};" for i, p in enumerate(pats)]
    lines += [f"parameter  BIST_STI_SIZE = {len(elements)};", "parameter  BIST_STI_WD   = 15;"]
    lines += [f"parameter  BIST_STIMULUS_TYPE{i+1} = 15'b{w:015b};" for i, w in enumerate(words)]
    lines += ["parameter  BIST_OP_SIZE        = 4;", "parameter  BIST_ERR_LIMIT           = 4;", "`endif"]
    (d / "mbist_def.svh").write_text("\n".join(lines) + "\n")
    return d


def fault_sample():
    rnd = random.Random(15)
    fs = []
    for _ in range(24):
        a, b = rnd.randrange(NW), rnd.randrange(W)
        fs.append(("SAF", rm.Fault("SAF", a, b, rnd.randint(0, 1))))
    for _ in range(48):
        a, b = rnd.randrange(NW), rnd.randrange(W)
        fs.append(("TF", rm.Fault("TF", a, b, rnd.randint(0, 1))))
    for _ in range(64):
        a, b = rnd.randrange(1, NW - 1), rnd.randrange(W)
        aa = a + rnd.choice((-1, 1))
        fs.append(("CF inter-word", rm.Fault("CF", a, b, rnd.randint(0, 1), aa, b, rnd.randint(0, 1))))
    for _ in range(48):
        a, b = rnd.randrange(NW), rnd.randrange(W)
        fs.append(("CF intra-word", rm.Fault("CF", a, b, rnd.randint(0, 1), a, b ^ 1, rnd.randint(0, 1))))
    return fs


def simulate(vvp, f):
    args = ["vvp", "-n", str(vvp), "+MAXC=40000000"]
    if f.kind == "CF":
        args += [f"+CA={f.a}", f"+CB={f.b}", f"+CAA={f.aa}", f"+CAB={f.ab}", f"+CT={f.t}", f"+CV={f.v}"]
    else:
        args += ["+N=1", f"+K0={0 if f.kind == 'SAF' else 1}", f"+A0={f.a}", f"+B0={f.b}", f"+V0={f.v}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=900).stdout
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
    ap.add_argument("--out", default=str(ROOT / "results" / "algorithms_rtl.csv"))
    args = ap.parse_args()
    fs = fault_sample()
    out = Path(args.out)
    done = set()
    if out.exists():
        done = {(r["algorithm"], r["fault"]) for r in csv.DictReader(open(out))}
    fh = open(out, "a", newline="")
    writer, lock = None, threading.Lock()
    for name, elements, bgs, shipped in ALGS:
        inc = INC if shipped else make_svh(name, elements, bgs)
        vvp = BUILD / f"{name.replace(' ', '_').replace(',', '').replace('.', '')}.vvp"
        subprocess.run(["bash", str(ROOT / "tb/mbist_ctrl/build.sh"), "-o", str(vvp), "-I", str(inc)], check=True)
        todo = [(c, f) for c, f in fs
                if (name, f"{f.kind},{f.a},{f.b},{f.v},{f.aa},{f.ab},{f.t}") not in done]
        print(f"{name}: {len(todo)} runs, stimulus {[format(w, '015b') for w in encode(elements)]}", flush=True)

        def work(cf):
            nonlocal writer
            cls, f = cf
            exp = rm.run_march(elements, NW, W, f, nrep=4, backgrounds=bgs)
            words = sorted(set(exp["fail_addrs"]))
            o = simulate(vvp, f)
            exp_det = int(bool(words))
            n = len(words)
            ok = (o.get("done") == 1 and o.get("error") == int(n > 4)
                  and (n > 4 or (o.get("correct") == int(n > 0) and o.get("cnt") == n and o["rep"] == words)))
            row = {"algorithm": name, "class": cls,
                   "fault": f"{f.kind},{f.a},{f.b},{f.v},{f.aa},{f.ab},{f.t}",
                   "golden_detect": exp_det, "dut_detect": int(o.get("cnt", 0) > 0 or o.get("error", 0) == 1),
                   "golden_words": " ".join(map(str, words)), "dut_repair": " ".join(map(str, o["rep"])),
                   "dut_done": o.get("done", 0), "dut_cnt": o.get("cnt", -1), "cycles": o.get("cycles", -1),
                   "match_golden": int(ok)}
            with lock:
                if writer is None:
                    writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
                    if not done:
                        writer.writeheader()
                writer.writerow(row)
                fh.flush()

        with ThreadPoolExecutor(args.jobs) as ex:
            list(ex.map(work, todo))
    fh.close()
    for n, why in UNENCODABLE:
        print(f"not encodable: {n} ({why})")
    print("->", out)


if __name__ == "__main__":
    main()
