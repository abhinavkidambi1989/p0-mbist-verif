#!/usr/bin/env bash
# Build the standalone mbist_ctrl simulation. Usage: bash tb/mbist_ctrl/build.sh [extra files...]
set -e
cd "$(dirname "$0")/../.."
D=duts/mbist_ctrl/verilog/rtl; R=$D/mbist
mkdir -p build
iverilog -g2005-sv -o build/mc.vvp -I $R/include -DFUNCTIONAL -DSIM \
  tb/mbist_ctrl/timescale.v \
  $R/src/top/mbist_top1.sv $R/src/core/*.sv $D/lib/reset_sync.sv tb/mbist_ctrl/stubs.v \
  tb/mbist_ctrl/sky130_sram_2kbyte_1rw1r_32x512_8_icarus.v tb/mbist_ctrl/tb_mbist_ctrl.v "$@" \
  -s tb_mbist_ctrl 2>&1 | grep -E " error|syntax" || true
