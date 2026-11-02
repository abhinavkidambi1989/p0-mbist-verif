#!/usr/bin/env bash
# One-time setup on Windows (WSL2 Ubuntu). Run from the repo folder:  bash setup_wsl.sh
set -e

echo "== 1/3 Installing simulators and tools (asks for your Ubuntu password) =="
sudo apt update
sudo apt install -y iverilog verilator gtkwave make git python3-venv python3-pip

echo "== 2/3 Creating Python environment and installing cocotb, pyuvm, plotting =="
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "== 3/3 Checking everything =="
echo -n "Icarus Verilog: "; iverilog -V 2>&1 | head -1
echo -n "Verilator:      "; verilator --version
echo -n "cocotb:         "; python -c "import cocotb; print(cocotb.__version__)"
echo -n "pyuvm:          "; python -c "import pyuvm; print('ok')"
echo -n "matplotlib:     "; python -c "import matplotlib; print(matplotlib.__version__)"
echo
echo "ALL DONE. Copy everything from '== 3/3' down and paste it to Claude."
