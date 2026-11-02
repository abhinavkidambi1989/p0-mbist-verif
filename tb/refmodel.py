"""Golden March-test reference model.

YOU write the logic here: this model is the paper's core contribution.
Interface below is only a suggestion so the scoreboard and campaigns can call it.

March notation used throughout: an element is (order, [ops]) where
  order in {"up", "down", "any"} and ops are strings like "w0", "r1".
March C- (full, 10N):
  [("any",["w0"]), ("up",["r0","w1"]), ("up",["r1","w0"]),
   ("down",["r0","w1"]), ("down",["r1","w0"]), ("any",["r0"])]
"""

MARCH_C_MINUS = [
    ("any", ["w0"]), ("up", ["r0", "w1"]), ("up", ["r1", "w0"]),
    ("down", ["r0", "w1"]), ("down", ["r1", "w0"]), ("any", ["r0"]),
]


class FaultyMemory:
    """Behavioural memory with injectable faults (SAF, TF, CF, AF). TODO: implement."""

    def __init__(self, depth: int, width: int, faults=None):
        self.depth, self.width, self.faults = depth, width, faults or []

    def write(self, addr: int, data: int) -> None:
        raise NotImplementedError

    def read(self, addr: int) -> int:
        raise NotImplementedError


def run_march(algorithm, memory: FaultyMemory, data_background: int = 0):
    """Apply a March algorithm to `memory`.

    Return the predicted outcome the DUT must match, e.g.
      {"fail": bool, "fail_addrs": [addr, ...] in detection order,
       "repair_entries": [...]}   # per the DUT's repair policy
    TODO: implement.
    """
    raise NotImplementedError
