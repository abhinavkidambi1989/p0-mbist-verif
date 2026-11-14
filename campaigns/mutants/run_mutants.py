"""Seeded-bug (mutation) campaign for both designs.

Each mutant is one single-line RTL change applied to a copy of the design sources. Every mutant
runs the same test set as the unmutated design. A mutant is KILLED at a checker level if, on some
test, the outputs visible at that level differ from the unmutated design's outputs:
  L0  DONE                               (completion only)
  L1  DONE + pass/fail flag(s)           (A: FAIL; B: ERROR)
  L1c L1 + CORRECT + error count         (B only; what B's own testbench signature checks)
  L2  L1c + every fail address (A) and the repair table (A and B)
A mutant that hangs (no DONE within the cycle budget) is killed at L0.
Writes results/mutants_<design>.csv.  Usage: python campaigns/mutants/run_mutants.py [A|B|both]
"""
import csv
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "mut"

# ---------------------------------------------------------------- Design A (TT #777)
A_SRC = ROOT / "duts" / "tt777" / "src"
A_FILES = ["memory.v", "mbisr_controller.v", "mbist_marchc_controller.v", "top.v"]
C, R = "mbist_marchc_controller.v", "mbisr_controller.v"
A_MUTANTS = [  # id, file, old, new, occurrence (1-based), description
    ("A01", C, "if (mem_rdata !== 0) begin", "if (mem_rdata[3:0] !== 4'h0) begin", 1, "r0 compare checks low nibble only (up element)"),
    ("A02", C, "if (mem_rdata !== {DATA_WIDTH{1'b1}}) begin", "if (mem_rdata[3:0] !== 4'hF) begin", 1, "r1 compare checks low nibble only"),
    ("A03", C, "if (mem_rdata !== 0) begin", "if (mem_rdata[3:0] !== 4'h0) begin", 2, "final r0 compare checks low nibble only"),
    ("A04", C, "addr <= addr + 1;", "addr <= addr + 2;", 2, "up element skips odd addresses"),
    ("A05", C, "mem_wdata <= {DATA_WIDTH{1'b1}};", "mem_wdata <= {DATA_WIDTH{1'b0}};", 1, "writes 0 instead of 1"),
    ("A06", C, "fail <= 1;", "fail <= 0;", 1, "FAIL not set by first element"),
    ("A07", C, "fail_addr <= read_addr;", "fail_addr <= addr;", 1, "fail address from wrong register"),
    ("A08", C, "state <= STATE_R0F;", "state <= STATE_DONE;", 1, "final read element skipped"),
    ("A09", C, "addr <= MAX_ADDR;", "addr <= MAX_ADDR - 1;", 1, "down element starts one address low"),
    ("A10", C, "done <= 1;", "done <= 0;", 1, "DONE never asserted"),
    ("A11", C, "fail_valid <= 1;", "fail_valid <= 0;", 2, "no fail report from down element"),
    ("A12", C, "fail_addr <= read_addr;", "fail_addr <= read_addr + 1;", 2, "down-element fail address +1"),
    ("A13", R, "remap_addr = SPARE_BASE + k[ADDR_WIDTH-1:0];", "remap_addr = SPARE_BASE;", 1, "all repairs map to spare 0"),
    ("A14", R, "inserted <= 1'b1;", "inserted <= 1'b0;", 1, "duplicate check disabled"),
    ("A15", R, "repair_valid[j] <= 1'b1;", "repair_valid[j] <= 1'b0;", 1, "repair entry never marked valid"),
    ("A16", R, "repair_table[j] <= bist_fail_addr;", "repair_table[j] <= bist_fail_addr + 1'b1;", 1, "repair stores address +1"),
]

# ---------------------------------------------------------------- Design B (mbist_ctrl)
B_RTL = ROOT / "duts" / "mbist_ctrl" / "verilog" / "rtl"
AG, DC, RP, FS, PS, SS = ("mbist_addr_gen.sv", "mbist_data_cmp.sv", "mbist_repair_addr.sv",
                          "mbist_fsm.sv", "mbist_pat_sel.sv", "mbist_sti_sel.sv")
B_MUTANTS = [
    ("B01", AG, "(bist_addr == end_addr))||", "(bist_addr == end_addr-1'b1))||", 1, "up element ends one address early"),
    ("B02", AG, "bist_addr+1'b1:bist_addr-1'b1", "bist_addr+2'd2:bist_addr-1'b1", 1, "up element skips odd addresses"),
    ("B03", AG, "((updown == 1'b0)&&(bist_addr == start_addr))", "((updown == 1'b0)&&(bist_addr == start_addr+1'b1))", 1, "down element ends one address early"),
    ("B04", DC, "(read_invert) ? ~comp_data: comp_data", "comp_data", 1, "read-invert ignored in expected data"),
    ("B05", DC, "|(exp_data ^ rxd_data)", "|(exp_data[15:0] ^ rxd_data[15:0])", 1, "upper 16 data bits not compared"),
    ("B06", DC, "error_addr  <= addr;", "error_addr  <= addr+1'b1;", 1, "error address +1"),
    ("B07", DC, "else if(comp_status && (error_cnt < BIST_ERR_LIMIT) )", "else if(comp_status && (error_cnt < BIST_ERR_LIMIT-1) )", 1, "error limit 3 instead of 4"),
    ("B08", DC, "correct      <='b1;", "correct      <='b0;", 1, "CORRECT never set"),
    ("B09", DC, "error        <= '1;", "error        <= '0;", 1, "ERROR never set"),
    ("B10", DC, "? comp_status : 1'b0;", "? 1'b0 : 1'b0;", 1, "no repair request issued"),
    ("B11", RP, "RepairMem[ErrorCnt] <= ErrorAddr;", "RepairMem[0] <= ErrorAddr;", 1, "every repair overwrites entry 0"),
    ("B12", RP, "AddressOut = BIST_REPAIR_ADDR_START+index;", "AddressOut = BIST_REPAIR_ADDR_START;", 1, "all repairs map to spare 0"),
    ("B13", RP, "if(ErrorCnt > index && AddressIn", "if(ErrorCnt >= index && AddressIn", 1, "remap also uses an unwritten entry"),
    ("B14", FS, "(last_addr && last_op && last_sti && last_pat) || bist_error", "(last_addr && last_op && last_sti) || bist_error", 1, "stops after first data background"),
    ("B15", FS, "(last_addr && last_op && last_sti && last_pat) || bist_error", "(last_addr && last_op && last_sti && last_pat)", 1, "does not abort on unrepairable error"),
    ("B16", PS, "else if(run)         pat_sel <= {pat_sel[0],pat_sel[BIST_DATA_PAT_SIZE-1:1]};", "else if(run)         pat_sel <= pat_sel;", 1, "data background never advances"),
    ("B17", SS, "else if(run)         sti_sel <= {sti_sel[0],sti_sel[BIST_STI_SIZE-1:1]};", "else if(run)         sti_sel <= {sti_sel[0],sti_sel[0],sti_sel[BIST_STI_SIZE-1:2]};", 1, "one March element skipped"),
    ("B18", RP, "Correct         <= 1'b1;", "Correct         <= 1'b0;", 1, "repair-side CORRECT never set"),
]


def apply(src_dir, files, dst, mut):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src_dir, dst)
    if mut is None:
        return
    _, f, old, new, nth, _ = mut
    p = dst / f
    s = p.read_text()
    idx = -1
    for _ in range(nth):
        idx = s.index(old, idx + 1)  # raises if not found
    p.write_text(s[:idx] + new + s[idx + len(old):])


# ---------------------------------------------------------------- simulation
def build_a(d):
    out = d / "sim.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(out), *[str(d / f) for f in A_FILES],
                    str(ROOT / "tb" / "tt777" / "tb_tt777_fault.v")], check=True,
                   capture_output=True)
    return out


def tests_a():
    t = [None]
    for a in range(32):
        for b in (0, 7):
            for v in (0, 1):
                t.append(("SAF", a, b, v))
                t.append(("TF", a, b, v))
    return t


def sim_a(vvp, t):
    args = ["vvp", "-n", str(vvp)]
    if t:
        k, a, b, v = t
        args += [f"+FT={ {'SAF': 0, 'TF': 1}[k] }", f"+A={a}", f"+B={b}", f"+V={v}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=120).stdout
    o = {"done": 0, "flag": 0, "addrs": [], "rep": []}
    for line in out.splitlines():
        p = line.split()
        if p[:2] == ["RESULT", "failaddr"]:
            o["addrs"].append(int(p[2]))
        elif p[:2] == ["RESULT", "done"]:
            o["done"], o["flag"] = int(p[2]), int(p[4])
        elif p[:2] == ["RESULT", "repair"] and p[3] == "1":
            o["rep"].append(p[4])
    return o


def build_b(d):
    out = d / "sim.vvp"
    core = d / "core"
    subprocess.run(["iverilog", "-g2005-sv", "-o", str(out), "-I", str(B_RTL / "mbist" / "include"),
                    "-DFUNCTIONAL", "-DSIM", str(ROOT / "tb/mbist_ctrl/timescale.v"),
                    str(B_RTL / "mbist/src/top/mbist_top1.sv"), *sorted(str(p) for p in core.glob("*.sv")),
                    str(B_RTL / "lib/reset_sync.sv"), str(ROOT / "tb/mbist_ctrl/stubs.v"),
                    str(ROOT / "tb/mbist_ctrl/sky130_sram_2kbyte_1rw1r_32x512_8_icarus.v"),
                    str(ROOT / "tb/mbist_ctrl/tb_mbist_ctrl.v"), "-s", "tb_mbist_ctrl"],
                   check=True, capture_output=True)
    return out


def tests_b():
    return [[], [(0, 200, 5, 0)], [(0, 0, 0, 1)], [(0, 507, 31, 0)], [(1, 300, 17, 1)],
            [(0, 50, 2, 1), (0, 250, 20, 0), (0, 450, 9, 1)],
            [(0, 10, 1, 0), (0, 110, 12, 1), (0, 210, 23, 0), (0, 310, 30, 1), (0, 410, 4, 0)]]


def sim_b(vvp, faults):
    args = ["vvp", "-n", str(vvp), f"+N={len(faults)}", "+MAXC=400000"]
    for i, (k, a, b, v) in enumerate(faults):
        args += [f"+K{i}={k}", f"+A{i}={a}", f"+B{i}={b}", f"+V{i}={v}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=600).stdout
    o = {"done": 0, "flag": 0, "correct": 0, "cnt": 0, "rep": []}
    rc = 0
    for line in out.splitlines():
        p = line.split()
        if p[:2] == ["RESULT", "done"]:
            o.update(done=int(p[2]), flag=int(p[4]), correct=int(p[6]), cnt=int(p[8]))
        elif p[:2] == ["RESULT", "repcnt"]:
            rc = int(p[2]) if p[2] != "x" else 0
        elif p[:2] == ["RESULT", "repair"]:
            o["rep"].append(p[3])
    o["rep"] = sorted(o["rep"][:min(rc, 4)])
    return o


def levels(o, ref, design):
    l0 = o["done"] != ref["done"]
    l1 = l0 or o["flag"] != ref["flag"]
    if design == "A":
        l1c = l1
        l2 = l1 or o["addrs"] != ref["addrs"] or sorted(o["rep"]) != sorted(ref["rep"])
    else:
        l1c = l1 or o["correct"] != ref["correct"] or o["cnt"] != ref["cnt"]
        l2 = l1c or o["rep"] != ref["rep"]
    return l0, l1, l1c, l2


def run_design(design):
    if design == "A":
        src, files, muts, build, tests, sim, jobs = A_SRC, A_FILES, A_MUTANTS, build_a, tests_a(), sim_a, 2
    else:
        src, files, muts, build, tests, sim, jobs = B_RTL / "mbist/src/core", None, B_MUTANTS, build_b, tests_b(), sim_b, 2
    base_dir = BUILD / design / "orig"
    apply(src, files, base_dir if design == "A" else base_dir / "core", None)
    vvp = build(base_dir)
    with ThreadPoolExecutor(jobs) as ex:
        ref = list(ex.map(lambda t: sim(vvp, t), tests))
    rows = []
    for m in muts:
        d = BUILD / design / m[0]
        apply(src, files, d if design == "A" else d / "core", m)
        mv = build(d)
        with ThreadPoolExecutor(jobs) as ex:
            obs = list(ex.map(lambda t: sim(mv, t), tests))
        k = [any(levels(o, r, design)[i] for o, r in zip(obs, ref)) for i in range(4)]
        first = next((i for i, (o, r) in enumerate(zip(obs, ref)) if levels(o, r, design)[3]), -1)
        rows.append({"design": design, "id": m[0], "file": m[1], "description": m[5],
                     "killed_L0": int(k[0]), "killed_L1": int(k[1]), "killed_L1c": int(k[2]),
                     "killed_L2": int(k[3]), "tests": len(tests), "first_kill_test": first})
        print(m[0], k, flush=True)
    out = ROOT / "results" / f"mutants_{'tt777' if design == 'A' else 'mbist_ctrl'}.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("->", out)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    for d in (["A", "B"] if which == "both" else [which]):
        run_design(d)
