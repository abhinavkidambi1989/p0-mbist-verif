# mbist_ctrl bring-up status (9 Nov 2026)

- Standalone harness: `tb_mbist_ctrl.v` = `mbist_top1` + one 512x32 sky130 SRAM model, wired as in `user_project_wrapper.v`.
- `stubs.v` replaces SkyWater std cells (ctech_*) and the clock-skew delay chain with behavioural pass-throughs (no PDK needed).
- `sky130_sram_2kbyte_1rw1r_32x512_8_icarus.v`: upstream SRAM model with the `mem` declaration moved before first use (Icarus 13 rejects the forward reference). No functional change.
- Compiles with Icarus Verilog (iverilog -g2005-sv). First stimulus completes (all addresses); in the second stimulus the run stalls at address 0:
  `bist_error_correct` (re_init) goes X for one cycle per operation, so `last_op` = re_init ? 0 : op_sel[0] is X and the FSM never advances.
- Suspected cause: X read data from the SRAM behavioural model (dout1 driven X at posedge + T_HOLD, uninitialised words, or simultaneous read/write warning) reaching the compare. Not yet confirmed whether this is harness/simulator-specific or a real design issue.
- Next: (1) trace rxd_data/comp_status at the X cycle; (2) cross-check with Verilator (2-state); (3) if needed run the upstream Caravel test environment.
