// Directed smoke testbench for Tiny Tapeout #777 (tt_um_aksp_mbist_mbisr), DUT = `top`.
// Runs one MBIST pass with optional injected stuck-at faults and prints everything the
// golden model / scoreboard will later check: DONE, FAIL, every fail_valid/fail_addr
// pulse, and the final repair (CAM) table.
//
// Fault injection (behavioural, no RTL edits): up to 2 stuck-at faults on memory cells.
//   +F0_ADDR=<n> +F0_BIT=<b> +F0_VAL=<0|1>   (same for F1_*)   ; omit for fault-free run
// Every value printed with a "RESULT" prefix so scripts can collect it into CSV.
`timescale 1ns/1ps
module tb_tt777;
  localparam AW = 5, DW = 8, NREP = 2;

  reg clk = 0, rst = 1, start = 0;
  wire done, fail;
  always #5 clk = ~clk;

  top dut (.clk(clk), .rst(rst), .start(start), .done(done), .fail(fail));

  // ---------------- fault injection ----------------
  integer f0a = -1, f0b = 0, f0v = 0, f1a = -1, f1b = 0, f1v = 0;
  initial begin
    if (!$value$plusargs("F0_ADDR=%d", f0a)) f0a = -1;
    void'($value$plusargs("F0_BIT=%d", f0b));
    void'($value$plusargs("F0_VAL=%d", f0v));
    if (!$value$plusargs("F1_ADDR=%d", f1a)) f1a = -1;
    void'($value$plusargs("F1_BIT=%d", f1b));
    void'($value$plusargs("F1_VAL=%d", f1v));
  end
  // Re-apply the stuck value just after every clock edge, so any write is overridden
  // before the next read samples the array.
  always @(posedge clk) begin
    #1;
    if (f0a >= 0) dut.u_memory.mem_array[f0a][f0b] = f0v[0];
    if (f1a >= 0) dut.u_memory.mem_array[f1a][f1b] = f1v[0];
  end

  // ---------------- monitors ----------------
  integer nfail = 0;
  always @(posedge clk)
    if (dut.bist_fail_valid) begin
      $display("RESULT fail_valid t=%0t addr=%0d state=%0d", $time, dut.bist_fail_addr, dut.u_mbist.state);
      nfail = nfail + 1;
    end

  integer cycles = 0, i;
  initial begin
    repeat (4) @(posedge clk);
    rst = 0;
    @(posedge clk); start = 1;
    @(posedge clk); start = 0;
    while (!done && cycles < 5000) begin @(posedge clk); cycles = cycles + 1; end

    $display("RESULT faults f0=(%0d,%0d,%0d) f1=(%0d,%0d,%0d)", f0a, f0b, f0v, f1a, f1b, f1v);
    $display("RESULT done=%0d fail=%0d cycles=%0d fail_pulses=%0d", done, fail, cycles, nfail);
    for (i = 0; i < NREP; i = i + 1)
      $display("RESULT repair[%0d] valid=%0d addr=%0d", i,
               dut.u_mbisr.repair_valid[i], dut.u_mbisr.repair_table[i]);
    $finish;
  end
endmodule
