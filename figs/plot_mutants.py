"""Fig. 3: mutants detected by checker level, per DUT.

Expects results/mutants_<dut>.csv with columns:
  mutant_id, dut, caught_donefail, caught_assert, caught_scoreboard   (0/1)
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
plt.style.use(ROOT / "figs" / "style.mplstyle")

files = sorted((ROOT / "results").glob("mutants_*.csv"))
if not files:
    raise SystemExit("no results/mutants_*.csv yet - run `make mutants` first")

df = pd.concat(pd.read_csv(f) for f in files)
# cumulative checker levels: (a) DONE/FAIL, (b) + assertions, (c) + scoreboard
df["lvl_b"] = df[["caught_donefail", "caught_assert"]].max(axis=1)
df["lvl_c"] = df[["caught_donefail", "caught_assert", "caught_scoreboard"]].max(axis=1)
rates = df.groupby("dut")[["caught_donefail", "lvl_b", "lvl_c"]].mean() * 100

ax = rates.plot.bar(rot=0, width=0.75)
ax.set_ylabel("Mutants detected (%)")
ax.set_xlabel("")
ax.set_ylim(0, 100)
ax.legend(["DONE/FAIL only", "+ assertions", "+ reference-model scoreboard"],
          loc="lower right", frameon=False)
plt.savefig(ROOT / "figs" / "fig3_mutants.pdf")
print("wrote figs/fig3_mutants.pdf")
