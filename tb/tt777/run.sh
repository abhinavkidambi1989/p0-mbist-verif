#!/usr/bin/env bash
# Compile #777 + testbench once, then run the directed tests.  Usage: bash tb/tt777/run.sh
set -e
cd "$(dirname "$0")/../.."
SRC=duts/tt777/src
mkdir -p build
iverilog -g2012 -o build/tt777.vvp \
  $SRC/memory.v $SRC/mbisr_controller.v $SRC/mbist_marchc_controller.v $SRC/top.v \
  tb/tt777/tb_tt777.v

run() { echo "=== $1"; shift; vvp -n build/tt777.vvp "$@" | grep RESULT; }

run "T0 fault-free"
run "T1 one stuck-at-0, addr 5 bit 0"          +F0_ADDR=5 +F0_BIT=0 +F0_VAL=0
run "T2 two stuck-at-0, addr 5 and addr 9"     +F0_ADDR=5 +F0_BIT=0 +F0_VAL=0 +F1_ADDR=9 +F1_BIT=3 +F1_VAL=0
run "T3 stuck-at-1, addr 12 bit 7"             +F0_ADDR=12 +F0_BIT=7 +F0_VAL=1
run "T4 fault in spare row, addr 30"           +F0_ADDR=30 +F0_BIT=0 +F0_VAL=0
run "T5 stuck-at-0, addr 0 (boundary)"         +F0_ADDR=0 +F0_BIT=0 +F0_VAL=0
run "T6 stuck-at-1, addr 31 (boundary)"        +F0_ADDR=31 +F0_BIT=0 +F0_VAL=1
