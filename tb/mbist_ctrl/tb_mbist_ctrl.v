// Standalone testbench for dineshannayya/mbist_ctrl (mbist_top1 + one 512x32 sky130 SRAM model),
// wired exactly as in the chip's user_project_wrapper.v (port 0 = BIST write, port 1 = BIST read).
// MBIST runs with its reset-default configuration (bist_en = bist_run = 1, no scan load):
// 8 data backgrounds x 5 March stimuli over addresses 0x000-0x1FB, spares 0x1FC-0x1FF.
//
// Fault injection (behavioural, on the SRAM array, no RTL edits). Up to 8 faults:
//   +N=<count>  and for i = 0..N-1:  +K<i>=<0 SAF | 1 TF>  +A<i>=<word>  +B<i>=<bit>  +V<i>=<value>
//   SAF: bit stuck at V.   TF: the V-transition fails (V=1: 0->1 fails, V=0: 1->0 fails).
// Corrections are applied 2 ns after each edge of the write clock (writes land on its negedge).
// Output: RESULT lines with DONE/ERROR/CORRECT/error count and the port-A repair table.
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

  // ---------------- fault injection ----------------
  integer nf = 0, i, t, k [0:7], a [0:7], b [0:7], v [0:7];
  reg prev [0:7];
  initial begin
    void'($value$plusargs("N=%d", nf));
    for (i = 0; i < 8; i = i + 1) begin
      k[i] = 0; a[i] = 0; b[i] = 0; v[i] = 0; prev[i] = 1'bx;
    end
    if (nf > 0) begin t=0; void'($value$plusargs("K0=%d",t)); k[0]=t; t=0; void'($value$plusargs("A0=%d",t)); a[0]=t; t=0; void'($value$plusargs("B0=%d",t)); b[0]=t; t=0; void'($value$plusargs("V0=%d",t)); v[0]=t; end
    if (nf > 1) begin t=0; void'($value$plusargs("K1=%d",t)); k[1]=t; t=0; void'($value$plusargs("A1=%d",t)); a[1]=t; t=0; void'($value$plusargs("B1=%d",t)); b[1]=t; t=0; void'($value$plusargs("V1=%d",t)); v[1]=t; end
    if (nf > 2) begin t=0; void'($value$plusargs("K2=%d",t)); k[2]=t; t=0; void'($value$plusargs("A2=%d",t)); a[2]=t; t=0; void'($value$plusargs("B2=%d",t)); b[2]=t; t=0; void'($value$plusargs("V2=%d",t)); v[2]=t; end
    if (nf > 3) begin t=0; void'($value$plusargs("K3=%d",t)); k[3]=t; t=0; void'($value$plusargs("A3=%d",t)); a[3]=t; t=0; void'($value$plusargs("B3=%d",t)); b[3]=t; t=0; void'($value$plusargs("V3=%d",t)); v[3]=t; end
    if (nf > 4) begin t=0; void'($value$plusargs("K4=%d",t)); k[4]=t; t=0; void'($value$plusargs("A4=%d",t)); a[4]=t; t=0; void'($value$plusargs("B4=%d",t)); b[4]=t; t=0; void'($value$plusargs("V4=%d",t)); v[4]=t; end
    if (nf > 5) begin t=0; void'($value$plusargs("K5=%d",t)); k[5]=t; t=0; void'($value$plusargs("A5=%d",t)); a[5]=t; t=0; void'($value$plusargs("B5=%d",t)); b[5]=t; t=0; void'($value$plusargs("V5=%d",t)); v[5]=t; end
    if (nf > 6) begin t=0; void'($value$plusargs("K6=%d",t)); k[6]=t; t=0; void'($value$plusargs("A6=%d",t)); a[6]=t; t=0; void'($value$plusargs("B6=%d",t)); b[6]=t; t=0; void'($value$plusargs("V6=%d",t)); v[6]=t; end
    if (nf > 7) begin t=0; void'($value$plusargs("K7=%d",t)); k[7]=t; t=0; void'($value$plusargs("A7=%d",t)); a[7]=t; t=0; void'($value$plusargs("B7=%d",t)); b[7]=t; t=0; void'($value$plusargs("V7=%d",t)); v[7]=t; end
  end

  integer j;
  reg cur;
  always @(negedge mem_clk_b or posedge mem_clk_b) begin
    #2;
    for (j = 0; j < nf; j = j + 1) begin
      cur = sram.mem[a[j]][b[j]];
      if (k[j] == 0) sram.mem[a[j]][b[j]] = v[j][0];
      else begin
        if (v[j] == 1 && prev[j] === 1'b0 && cur === 1'b1) sram.mem[a[j]][b[j]] = 1'b0;
        if (v[j] == 0 && prev[j] === 1'b1 && cur === 1'b0) sram.mem[a[j]][b[j]] = 1'b1;
      end
      prev[j] = sram.mem[a[j]][b[j]];
    end
  end


  // ---------------- optional waveform dump (+VCD=<file>) ----------------
  wire [8:0]  w_bist_addr = dut.bist_addr;
  wire        w_rd = dut.op_read, w_wr = dut.op_write, w_cmp = dut.u_cmp.compare;
  wire [31:0] w_exp = dut.u_cmp.exp_data, w_rxd = dut.u_cmp.rxd_data;
  wire        w_errcor = dut.bist_error_correct;
  wire [3:0]  w_repcnt = dut.u_mem_sel.u_repair_A.ErrorCnt;
  wire [8:0]  w_rep0 = dut.u_mem_sel.u_repair_A.RepairMem[0];
  wire [8:0]  w_mem_addr_a = mem_addr_a, w_mem_addr_b = mem_addr_b;
  wire        w_cen_a = mem_cen_a, w_web_b = mem_web_b;
  reg  [8*64-1:0] vcdname;
  initial if ($value$plusargs("VCD=%s", vcdname)) begin $dumpfile(vcdname); $dumpvars(1, tb_mbist_ctrl); end
  always @(posedge dut.bist_error_correct) $display("RESULT errcor_at %0t addr %0d", $time, dut.bist_error_addr);

  integer writes = 0, reads = 0;
  always @(posedge mem_clk_b) if (!mem_cen_b && !mem_web_b) writes = writes + 1;
  always @(posedge mem_clk_a) if (!mem_cen_a) reads = reads + 1;

  integer cyc = 0, MAXC = 2000000, r;
  initial void'($value$plusargs("MAXC=%d", MAXC));
  initial begin
    repeat (10) @(posedge clk); rst_n = 1;
    while (!bist_done && cyc < MAXC) begin @(posedge clk); cyc = cyc + 1; end
    repeat (20) @(posedge clk);
    $display("RESULT done %0d error %0d correct %0d errcnt %0d cycles %0d writes %0d reads %0d",
             bist_done, bist_error, bist_correct, bist_error_cnt, cyc, writes, reads);
    $display("RESULT repcnt %0d", dut.u_mem_sel.u_repair_A.ErrorCnt);
    for (r = 0; r < 4; r = r + 1)
      $display("RESULT repair %0d %0d", r, dut.u_mem_sel.u_repair_A.RepairMem[r]);
    $finish;
  end
endmodule
