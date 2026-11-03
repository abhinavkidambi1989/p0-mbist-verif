// All-in-one directed testbench for Tiny Tapeout #777 (DUT = `top`).
// Runs 7 scenarios back to back (reset between each) so it works in one EDA Playground run.
// Fault model: up to two stuck-at cells, re-applied just after every clock edge.
`timescale 1ns/1ps
module tb_tt777_all;
  localparam NREP = 2;
  reg clk = 0, rst = 1, start = 0;
  wire done, fail;
  always #5 clk = ~clk;

  top dut (.clk(clk), .rst(rst), .start(start), .done(done), .fail(fail));

  integer f0a, f0b, f0v, f1a, f1b, f1v;
  always @(posedge clk) begin
    #1;
    if (f0a >= 0) dut.u_memory.mem_array[f0a][f0b] = f0v[0];
    if (f1a >= 0) dut.u_memory.mem_array[f1a][f1b] = f1v[0];
  end

  integer pulses;
  always @(posedge clk)
    if (dut.bist_fail_valid) begin
      $display("   fail_valid  fail_addr=%0d", dut.bist_fail_addr);
      pulses = pulses + 1;
    end

  task run_case(input [8*40-1:0] name, input integer a0, b0, v0, a1, b1, v1);
    integer cyc, i;
    begin
      f0a = a0; f0b = b0; f0v = v0; f1a = a1; f1b = b1; f1v = v1; pulses = 0;
      rst = 1; repeat (3) @(posedge clk); rst = 0;
      @(posedge clk); start = 1; @(posedge clk); start = 0;
      cyc = 0;
      while (!done && cyc < 5000) begin @(posedge clk); cyc = cyc + 1; end
      $display("%0s", name);
      $display("   DONE=%0d FAIL=%0d  fail pulses=%0d", done, fail, pulses);
      for (i = 0; i < NREP; i = i + 1)
        $display("   repair[%0d] valid=%0d addr=%0d", i,
                 dut.u_mbisr.repair_valid[i], dut.u_mbisr.repair_table[i]);
      @(posedge clk);
    end
  endtask

  initial begin
    f0a = -1; f1a = -1; f0b = 0; f0v = 0; f1b = 0; f1v = 0; pulses = 0;
    $dumpfile("dump.vcd"); $dumpvars(0, tb_tt777_all);
    run_case("T0 fault-free",                   -1,0,0, -1,0,0);
    run_case("T1 stuck-at-0 @ addr 5 bit 0",     5,0,0, -1,0,0);
    run_case("T2 stuck-at-0 @ addr 5 and 9",     5,0,0,  9,3,0);
    run_case("T3 stuck-at-1 @ addr 12 bit 7",   12,7,1, -1,0,0);
    run_case("T4 stuck-at-0 @ spare addr 30",   30,0,0, -1,0,0);
    run_case("T5 stuck-at-0 @ addr 0",           0,0,0, -1,0,0);
    run_case("T6 stuck-at-1 @ addr 31",         31,0,1, -1,0,0);
    $finish;
  end
endmodule
