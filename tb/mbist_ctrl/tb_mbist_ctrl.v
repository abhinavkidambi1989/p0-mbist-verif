// Standalone testbench for dineshannayya/mbist_ctrl (mbist_top1 + one 512x32 sky130 SRAM model),
// wired exactly as in the chip's user_project_wrapper.v (port 0 = BIST write, port 1 = BIST read).
// MBIST runs with its reset-default configuration (bist_en = bist_run = 1, no scan load).
// Optional single stuck-at fault on SRAM word A, bit B, value V:  +A=<n> +B=<b> +V=<0|1>
// The fault is applied by overriding the SRAM's stored word after every write cycle.
`timescale 1ns/100ps
module tb_mbist_ctrl;
  reg clk = 0, rst_n = 0;
  always #12.5 clk = ~clk;  // 40 MHz, as in the design's own test

  wire       bist_done, bist_error, bist_correct, bist_sdo;
  wire [3:0] bist_error_cnt;
  wire       mem_clk_a, mem_cen_a, mem_clk_b, mem_cen_b, mem_web_b;
  wire [8:0] mem_addr_a, mem_addr_b;
  wire [31:0] mem_din_b, mem_dout_a, wb_dat_o;
  wire [3:0] mem_mask_b;
  wire       wb_ack_o, wb_err_o, wbd_clk_mbist;

  mbist_top1 dut (
    .wbd_clk_int(clk), .wbd_clk_mbist(wbd_clk_mbist), .cfg_cska_mbist(4'h0),
    .rst_n(rst_n), .bist_en(1'b1), .bist_run(1'b1), .bist_shift(1'b0), .bist_load(1'b0), .bist_sdi(1'b0),
    .bist_error_cnt(bist_error_cnt), .bist_correct(bist_correct), .bist_error(bist_error),
    .bist_done(bist_done), .bist_sdo(bist_sdo),
    .wb_clk_i(clk), .wb_cyc_i(1'b0), .wb_stb_i(1'b0), .wb_adr_i(9'h0), .wb_we_i(1'b0),
    .wb_dat_i(32'h0), .wb_sel_i(4'h0), .wb_dat_o(wb_dat_o), .wb_ack_o(wb_ack_o), .wb_err_o(wb_err_o),
    .mem_clk_a(mem_clk_a), .mem_addr_a(mem_addr_a), .mem_cen_a(mem_cen_a), .mem_dout_a(mem_dout_a),
    .mem_clk_b(mem_clk_b), .mem_cen_b(mem_cen_b), .mem_web_b(mem_web_b), .mem_mask_b(mem_mask_b),
    .mem_addr_b(mem_addr_b), .mem_din_b(mem_din_b));

  sky130_sram_2kbyte_1rw1r_32x512_8 sram (
    .clk0(mem_clk_b), .csb0(mem_cen_b), .web0(mem_web_b), .wmask0(mem_mask_b),
    .addr0(mem_addr_b), .din0(mem_din_b), .dout0(),
    .clk1(mem_clk_a), .csb1(mem_cen_a), .addr1(mem_addr_a), .dout1(mem_dout_a));

  integer fa = -1, fb = 0, fv = 0;
  initial begin
    if (!$value$plusargs("A=%d", fa)) fa = -1;
    void'($value$plusargs("B=%d", fb));
    void'($value$plusargs("V=%d", fv));
  end
  // Stuck-at: keep forcing the stored bit after every edge of the write clock.
  always @(negedge mem_clk_b or posedge mem_clk_b) begin
    #2;
    if (fa >= 0) sram.mem[fa][fb] = fv[0];
  end

  integer writes = 0, reads = 0;
  always @(posedge mem_clk_b) if (!mem_cen_b && !mem_web_b) writes = writes + 1;
  always @(posedge mem_clk_a) if (!mem_cen_a) reads = reads + 1;

  integer cyc = 0;
  initial begin
    repeat (10) @(posedge clk); rst_n = 1;
    while (!bist_done && cyc < 2000000) begin @(posedge clk); cyc = cyc + 1; end
    repeat (20) @(posedge clk);
    $display("RESULT fault a=%0d b=%0d v=%0d", fa, fb, fv);
    $display("RESULT done %0d error %0d correct %0d errcnt %0d cycles %0d writes %0d reads %0d",
             bist_done, bist_error, bist_correct, bist_error_cnt, cyc, writes, reads);
    $finish;
  end
endmodule
