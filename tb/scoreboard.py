"""Compares DUT-observed MBIST/BISR results with the golden model's prediction."""

from dataclasses import dataclass, field


@dataclass
class Observed:
    done: bool = False
    fail: bool = False
    fail_addrs: list = field(default_factory=list)      # from fail_valid/fail_addr
    repair_entries: list = field(default_factory=list)  # read back from repair CAM/regs


def compare(expected: dict, observed: Observed) -> list:
    """Return a list of mismatch strings (empty list = pass)."""
    errs = []
    if not observed.done:
        errs.append("DONE never asserted")
    if observed.fail != expected["fail"]:
        errs.append(f"FAIL={observed.fail}, expected {expected['fail']}")
    if observed.fail_addrs != expected["fail_addrs"]:
        errs.append(f"fail_addrs {observed.fail_addrs} != {expected['fail_addrs']}")
    if "repair_entries" in expected and observed.repair_entries != expected["repair_entries"]:
        errs.append(f"repair {observed.repair_entries} != {expected['repair_entries']}")
    return errs
