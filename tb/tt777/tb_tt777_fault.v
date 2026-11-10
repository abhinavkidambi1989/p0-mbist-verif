// Fault-campaign testbench for Tiny Tapeout #777 (DUT = `top`). One fault per run.
// Fault models (behavioural, applied to the memory array, no RTL edits):
//   +FT=0 SAF : cell (A,B) stuck at V
//   +FT=1 TF  : cell (A,B) cannot make the V-transition (V=1: 0->1 fails, V=0: 1->0 fails)
//   +FT=2 CFid: when aggressor (AA,AB) makes transition T (T=1: up, 0: down), victim (A,B) is forced to V
//   FT absent : fault-free run
// Corrections are applied 1 ns after each clock edge, i.e. after the write and before the next read.
// Output: RESULT lines (fail pulses, DONE/FAIL, repair table) parsed by campaigns/faults/run.py.
`timescale 1ns/1ps
module tb_tt777_fault;
  localparam NREP = 2;
  reg clk = 0, rst = 1, start = 0;
  wire done, fail;
  always #5 clk = ~clk;
  top dut (.clk(clk), .rst(rst), .start(start), .done(done), .fail(fail));

  integer ft = -1, a = 0, b = 0, v = 0, aa = 0, ab = 0, tt = 1;
  reg vprev, aprev;
  initial begin
    void'($value$plusargs("FT=%d", ft));
    void'($value$plusargs("A=%d", a));  void'($value$plusargs("B=%d", b));
    void'($value$plusargs("V=%d", v));
    void'($value$plusargs("AA=%d", aa)); void'($value$plusargs("AB=%d", ab));
    void'($value$plusargs("T=%d", tt));
    vprev = 0; aprev = 0;
  end

  always @(posedge clk) begin
    #1;
    case (ft)
      0: dut.u_memory.mem_array[a][b] = v[0];
      1: begin
           if (v == 1 && vprev == 1'b0 && dut.u_memory.mem_array[a][b] == 1'b1) dut.u_memory.mem_array[a][b] = 1'b0;
           if (v == 0 && vprev == 1'b1 && dut.u_memory.mem_array[a][b] == 1'b0) dut.u_memory.mem_array[a][b] = 1'b1;
         end
      2: begin
           if ((tt == 1 && aprev == 1'b0 && dut.u_memory.mem_array[aa][ab] == 1'b1) ||
               (tt == 0 && aprev == 1'b1 && dut.u_memory.mem_array[aa][ab] == 1'b0))
             dut.u_memory.mem_array[a][b] = v[0];
         end
      default: ;
    endcase
    vprev = dut.u_memory.mem_array[a][b];
    aprev = dut.u_memory.mem_array[aa][ab];
  end

  always @(posedge clk)
    if (dut.bist_fail_valid) $display("RESULT failaddr %0d", dut.bist_fail_addr);

  integer cyc = 0, i;
  initial begin
    repeat (3) @(posedge clk); rst = 0;
    @(posedge clk); start = 1; @(posedge clk); start = 0;
    while (!done && cyc < 5000) begin @(posedge clk); cyc = cyc + 1; end
    $display("RESULT done %0d fail %0d", done, fail);
    for (i = 0; i < NREP; i = i + 1)
      $display("RESULT repair %0d %0d %0d", i, dut.u_mbisr.repair_valid[i], dut.u_mbisr.repair_table[i]);
    $finish;
  end
endmodule
