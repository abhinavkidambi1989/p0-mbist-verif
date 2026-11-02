# p0-mbist-verif

Reference-model-driven verification of MBIST and self-repair logic on open-source RTL.
Personal research project. Uses only public open-source designs, public standards and published literature.

## Designs under test (git submodules in `duts/`)
| DUT | Source | Licence | Repair |
|---|---|---|---|
| `tt777` | Tiny Tapeout IHP 26a #777 MBIST+MBISR 256x8 | confirm in its LICENSE | CAM remap, 16 entries |
| `mbist_ctrl` | github.com/dineshannayya/mbist_ctrl | Apache-2.0 | row redundancy |

Upstream RTL is never edited in place. Fault and mutant injection happen in wrappers or generated copies under `build/`.

## Setup
```bash
# 1. Simulators
#   Ubuntu/WSL2: sudo apt install iverilog verilator gtkwave
#   macOS:       brew install icarus-verilog verilator
# 2. Python env (3.11 or 3.12)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 3. Designs
git submodule add https://github.com/dineshannayya/mbist_ctrl duts/mbist_ctrl
git submodule add <tt777 repo URL from tinytapeout.com/chips/ttihp26a/777> duts/tt777
```

## Run
```bash
make sim DUT=tt777      # smoke test: fault-free memory, golden model must agree
make faults DUT=tt777   # fault-injection campaign  -> results/faults_<dut>.csv
make mutants DUT=tt777  # mutation campaign         -> results/mutants_<dut>.csv
make figs               # regenerate every figure   -> figs/*.pdf
```

## Layout
```
tb/          refmodel.py (golden March model), scoreboard.py, coverage.py, faults.py, test_*.py
campaigns/   scripts that run many simulations and write one CSV row per run
results/     CSV outputs only (all paper numbers come from here)
figs/        plot_*.py + style.mplstyle (IEEE column widths, Times 8 pt, vector PDF)
paper/       Overleaf git sync (IEEEtran conference)
```
