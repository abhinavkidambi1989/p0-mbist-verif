"""Golden March-test reference model (operation level).

Given a March algorithm, a memory geometry and one fault, predict what a *correct* MBIST
controller with built-in repair must report:
  fail          : True if any read mismatches
  fail_addrs    : address of every mismatching read, in test order (one entry per failing read)
  repair        : first `nrep` distinct failing addresses, in detection order
Spare rows are assumed fault-free and outside the tested address space (the documented intent).

March notation: list of (order, [ops]); order in {"up","down","any"}; ops "w0","w1","r0","r1".
"""

MARCH_TT777 = [  # algorithm implemented by TT #777 (shortened March C-, 4 elements)
    ("up", ["w0"]), ("up", ["r0", "w1"]), ("down", ["r1", "w0"]), ("up", ["r0"]),
]
MARCH_C_MINUS = [  # full March C- (10N)
    ("up", ["w0"]), ("up", ["r0", "w1"]), ("up", ["r1", "w0"]),
    ("down", ["r0", "w1"]), ("down", ["r1", "w0"]), ("up", ["r0"]),
]


class Fault:
    """kind: 'SAF' (a,b,v) | 'TF' (a,b,v = transition that fails: 1 = up, 0 = down)
             | 'CF' (victim a,b forced to v when aggressor aa,ab makes transition t)."""

    def __init__(self, kind, a, b, v, aa=None, ab=None, t=None):
        self.kind, self.a, self.b, self.v, self.aa, self.ab, self.t = kind, a, b, v, aa, ab, t

    def as_dict(self):
        return {"kind": self.kind, "a": self.a, "b": self.b, "v": self.v,
                "aa": self.aa, "ab": self.ab, "t": self.t}


class FaultyMemory:
    def __init__(self, depth, width, fault=None):
        self.depth, self.width, self.f = depth, width, fault
        self.m = [[0] * width for _ in range(depth)]
        self._fix()

    def _fix(self):
        f = self.f
        if f is not None and f.kind == "SAF":
            self.m[f.a][f.b] = f.v

    def write(self, addr, bitval):
        f, old = self.f, list(self.m[addr])
        for b in range(self.width):
            self.m[addr][b] = bitval
        if f is not None:
            if f.kind == "TF" and addr == f.a:
                o = old[f.b]
                if f.v == 1 and o == 0 and bitval == 1:
                    self.m[addr][f.b] = 0
                if f.v == 0 and o == 1 and bitval == 0:
                    self.m[addr][f.b] = 1
            if f.kind == "CF" and addr == f.aa:
                o, n = old[f.ab], self.m[addr][f.ab]
                if (f.t == 1 and o == 0 and n == 1) or (f.t == 0 and o == 1 and n == 0):
                    self.m[f.a][f.b] = f.v
        self._fix()

    def read(self, addr):
        return list(self.m[addr])


def run_march(algorithm, depth, width, fault=None, nrep=2):
    mem = FaultyMemory(depth, width, fault)
    fail_addrs = []
    for order, ops in algorithm:
        addrs = range(depth - 1, -1, -1) if order == "down" else range(depth)
        for a in addrs:
            for op in ops:
                val = int(op[1])
                if op[0] == "w":
                    mem.write(a, val)
                elif any(bit != val for bit in mem.read(a)):
                    fail_addrs.append(a)
    repair = []
    for a in fail_addrs:
        if a not in repair and len(repair) < nrep:
            repair.append(a)
    return {"fail": bool(fail_addrs), "fail_addrs": fail_addrs, "repair": repair}


if __name__ == "__main__":  # quick self-check against March theory
    D, W = 32, 8
    for alg, name in [(MARCH_TT777, "TT777"), (MARCH_C_MINUS, "March C-")]:
        saf = sum(run_march(alg, D, W, Fault("SAF", a, b, v))["fail"]
                  for a in range(D) for b in range(W) for v in (0, 1))
        tf = sum(run_march(alg, D, W, Fault("TF", a, b, v))["fail"]
                 for a in range(D) for b in range(W) for v in (0, 1))
        print(f"{name}: SAF {saf}/512 detected, TF {tf}/512 detected")
