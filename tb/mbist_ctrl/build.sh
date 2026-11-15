#!/usr/bin/env bash
# Build the standalone mbist_ctrl simulation.
# Usage: bash tb/mbist_ctrl/build.sh [-o out.vvp] [-I alt_include_dir] [-C alt_core_dir]
# -I / -C let a campaign substitute a generated mbist_def.svh (algorithm) or mutated core sources.
set -euo pipefail
cd "$(dirname "$0")/../.."
D=duts/mbist_ctrl/verilog/rtl; R=$D/mbist
OUT=build/mc.vvp; INC=$R/include; CORE=$R/src/core
while getopts "o:I:C:" o; do case $o in o) OUT=$OPTARG;; I) INC=$OPTARG;; C) CORE=$OPTARG;; esac; done
mkdir -p "$(dirname "$OUT")"
LOG=$(mktemp)
if ! iverilog -g2005-sv -o "$OUT.tmp" -I "$INC" -DFUNCTIONAL -DSIM \
    tb/mbist_ctrl/timescale.v \
    $R/src/top/mbist_top1.sv "$CORE"/*.sv $D/lib/reset_sync.sv tb/mbist_ctrl/stubs.v \
    tb/mbist_ctrl/sky130_sram_2kbyte_1rw1r_32x512_8_icarus.v tb/mbist_ctrl/tb_mbist_ctrl.v \
    -s tb_mbist_ctrl > "$LOG" 2>&1; then
  grep -vE "sorry|warning" "$LOG" >&2; rm -f "$LOG"; exit 1
fi
rm -f "$LOG"; mv "$OUT.tmp" "$OUT"
