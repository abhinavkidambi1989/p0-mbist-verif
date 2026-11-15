// Chip-level testbench for dineshannayya/mbist_ctrl: all eight MBIST/BISR instances of the chip's
// user_project_wrapper.v (4 x mbist_top1 + 512x32 SRAM, 4 x mbist_top2 + 256x32 SRAM) with the
// chip's glbl_cfg register block, wired as in the wrapper. The wb_host/UART bridge and the
// wb_interconnect are replaced by direct bus drivers: the interconnect passes BIST signals straight
// through (ch_data_out = ch_data_in), so the BIST wiring is unchanged.
//
// Sequence: reset -> write BIST_CTRL_2 (reg 3) = en+run for all eight -> poll BIST_STATUS_1/2
// (reg 4/5) until every DONE is set -> print both status words and every repair table ->
// clear BIST_CTRL_2 (functional mode) -> on every instance, write/read all user words with
// 00000000, FFFFFFFF, 00000000 over its functional bus (through the repair remap) and report
// the words that read back wrong.
//
// Faults (behavioural, on the SRAM arrays): +NF=<n>, for i < n: +FI<i>=<instance 0-7>
//   +FK<i>=<0 SAF | 1 TF> +FA<i>=<word> +FB<i>=<bit> +FV<i>=<value>   (up to 16 faults)
`timescale 1ns/100ps
module tb_mbist_sys;
  reg clk = 0, rst_n = 0;
  always #12.5 clk = ~clk;

  // ---------------- glbl_cfg (register block) ----------------
  reg        reg_cs = 0, reg_wr = 0;
  reg  [7:0] reg_addr = 0;
  reg [31:0] reg_wdata = 0;
  wire [31:0] reg_rdata;
  wire        reg_ack, wbd_clk_glbl;
  wire [7:0]  bist_en, bist_run, bist_load, bist_sdi, bist_shift, bist_sdo, bist_done, bist_error, bist_correct;
  wire [3:0]  ecnt [0:7];

  glbl_cfg u_glbl (
    .mclk(clk), .reset_n(rst_n), .wbd_clk_int(clk), .cfg_cska_glbl(4'h0), .wbd_clk_glbl(wbd_clk_glbl),
    .reg_cs(reg_cs), .reg_wr(reg_wr), .reg_addr(reg_addr), .reg_wdata(reg_wdata), .reg_be(4'hF),
    .reg_rdata(reg_rdata), .reg_ack(reg_ack),
    .bist_en(bist_en), .bist_run(bist_run), .bist_load(bist_load), .bist_sdi(bist_sdi), .bist_shift(bist_shift),
    .bist_sdo(bist_sdo), .bist_done(bist_done), .bist_error(bist_error), .bist_correct(bist_correct),
    .bist_error_cnt0(ecnt[0]), .bist_error_cnt1(ecnt[1]), .bist_error_cnt2(ecnt[2]), .bist_error_cnt3(ecnt[3]),
    .bist_error_cnt4(ecnt[4]), .bist_error_cnt5(ecnt[5]), .bist_error_cnt6(ecnt[6]), .bist_error_cnt7(ecnt[7]));

  // ---------------- functional bus drivers, one per instance ----------------
  reg  [7:0]  wcyc = 0, wstb = 0, wwe = 0;
  reg  [8:0]  wadr [0:7];
  reg  [31:0] wdat [0:7];
  wire [31:0] rdat [0:7];
  wire [7:0]  wack;

  // ---------------- fault list ----------------
  integer nf = 0, fi [0:15], fk [0:15], fa [0:15], fb [0:15], fv [0:15], q, t;
  reg [8*8:1] nm;
  initial begin
    void'($value$plusargs("NF=%d", nf));
    for (q = 0; q < 16; q = q + 1) begin
      fi[q] = -1; fk[q] = 0; fa[q] = 0; fb[q] = 0; fv[q] = 0;
      if (q < nf) begin
        $sformat(nm, "FI%0d=%%d", q); t = -1; void'($value$plusargs(nm, t)); fi[q] = t;
        $sformat(nm, "FK%0d=%%d", q); t = 0;  void'($value$plusargs(nm, t)); fk[q] = t;
        $sformat(nm, "FA%0d=%%d", q); t = 0;  void'($value$plusargs(nm, t)); fa[q] = t;
        $sformat(nm, "FB%0d=%%d", q); t = 0;  void'($value$plusargs(nm, t)); fb[q] = t;
        $sformat(nm, "FV%0d=%%d", q); t = 0;  void'($value$plusargs(nm, t)); fv[q] = t;
      end
    end
  end
  reg dump = 0;

  // ---------------- eight MBIST + SRAM instances ----------------
  genvar g;
  generate for (g = 0; g < 8; g = g + 1) begin : inst
    localparam AW = (g < 4) ? 9 : 8;
    wire          mclk_a, mcen_a, mclk_b, mcen_b, mweb_b, wclk;
    wire [AW-1:0] maddr_a, maddr_b;
    wire [31:0]   mdout_a, mdin_b;
    wire [3:0]    mmask_b;
    if (g < 4) begin : b
      mbist_top1 u_mb (
        .wbd_clk_int(clk), .wbd_clk_mbist(wclk), .cfg_cska_mbist(4'h0), .rst_n(rst_n),
        .bist_en(bist_en[g]), .bist_run(bist_run[g]), .bist_shift(bist_shift[g]), .bist_load(bist_load[g]),
        .bist_sdi(bist_sdi[g]), .bist_error_cnt(ecnt[g]), .bist_correct(bist_correct[g]),
        .bist_error(bist_error[g]), .bist_done(bist_done[g]), .bist_sdo(bist_sdo[g]),
        .wb_clk_i(clk), .wb_cyc_i(wcyc[g]), .wb_stb_i(wstb[g]), .wb_adr_i(wadr[g][AW-1:0]), .wb_we_i(wwe[g]),
        .wb_dat_i(wdat[g]), .wb_sel_i(4'hF), .wb_dat_o(rdat[g]), .wb_ack_o(wack[g]), .wb_err_o(),
        .mem_clk_a(mclk_a), .mem_addr_a(maddr_a), .mem_cen_a(mcen_a), .mem_dout_a(mdout_a),
        .mem_clk_b(mclk_b), .mem_cen_b(mcen_b), .mem_web_b(mweb_b), .mem_mask_b(mmask_b),
        .mem_addr_b(maddr_b), .mem_din_b(mdin_b));
      sky130_sram_2kbyte_1rw1r_32x512_8 sram (
        .clk0(mclk_b), .csb0(mcen_b), .web0(mweb_b), .wmask0(mmask_b), .addr0(maddr_b), .din0(mdin_b), .dout0(),
        .clk1(mclk_a), .csb1(mcen_a), .addr1(maddr_a), .dout1(mdout_a));
      always @(posedge dump) begin : d
        integer r;
        $display("RESULT inst %0d repcnt %0d", g, u_mb.u_mem_sel.u_repair_A.ErrorCnt);
        for (r = 0; r < 4; r = r + 1)
          $display("RESULT inst %0d repair %0d %0d", g, r, u_mb.u_mem_sel.u_repair_A.RepairMem[r]);
      end
    end else begin : b
      mbist_top2 u_mb (
        .wbd_clk_int(clk), .wbd_clk_mbist(wclk), .cfg_cska_mbist(4'h0), .rst_n(rst_n),
        .bist_en(bist_en[g]), .bist_run(bist_run[g]), .bist_shift(bist_shift[g]), .bist_load(bist_load[g]),
        .bist_sdi(bist_sdi[g]), .bist_error_cnt(ecnt[g]), .bist_correct(bist_correct[g]),
        .bist_error(bist_error[g]), .bist_done(bist_done[g]), .bist_sdo(bist_sdo[g]),
        .wb_clk_i(clk), .wb_cyc_i(wcyc[g]), .wb_stb_i(wstb[g]), .wb_adr_i(wadr[g][AW-1:0]), .wb_we_i(wwe[g]),
        .wb_dat_i(wdat[g]), .wb_sel_i(4'hF), .wb_dat_o(rdat[g]), .wb_ack_o(wack[g]), .wb_err_o(),
        .mem_clk_a(mclk_a), .mem_addr_a(maddr_a), .mem_cen_a(mcen_a), .mem_dout_a(mdout_a),
        .mem_clk_b(mclk_b), .mem_cen_b(mcen_b), .mem_web_b(mweb_b), .mem_mask_b(mmask_b),
        .mem_addr_b(maddr_b), .mem_din_b(mdin_b));
      sky130_sram_1kbyte_1rw1r_32x256_8 sram (
        .clk0(mclk_b), .csb0(mcen_b), .web0(mweb_b), .wmask0(mmask_b), .addr0(maddr_b), .din0(mdin_b), .dout0(),
        .clk1(mclk_a), .csb1(mcen_a), .addr1(maddr_a), .dout1(mdout_a));
      always @(posedge dump) begin : d
        integer r;
        $display("RESULT inst %0d repcnt %0d", g, u_mb.u_mem_sel.u_repair_A.ErrorCnt);
        for (r = 0; r < 4; r = r + 1)
          $display("RESULT inst %0d repair %0d %0d", g, r, u_mb.u_mem_sel.u_repair_A.RepairMem[r]);
      end
    end
    // fault injection on this instance's array, just after each write-port clock edge
    integer j;
    reg cur;
    reg prev [0:15];
    initial for (j = 0; j < 16; j = j + 1) prev[j] = 1'bx;
    always @(negedge mclk_b or posedge mclk_b) begin
      #2;
      for (j = 0; j < nf; j = j + 1) if (fi[j] == g) begin
        cur = b.sram.mem[fa[j]][fb[j]];
        if (fk[j] == 0) b.sram.mem[fa[j]][fb[j]] = fv[j][0];
        else begin
          if (fv[j] == 1 && prev[j] === 1'b0 && cur === 1'b1) b.sram.mem[fa[j]][fb[j]] = 1'b0;
          if (fv[j] == 0 && prev[j] === 1'b1 && cur === 1'b0) b.sram.mem[fa[j]][fb[j]] = 1'b1;
        end
        prev[j] = b.sram.mem[fa[j]][fb[j]];
      end
    end
  end endgenerate

  // ---------------- bus tasks ----------------
  task reg_access(input wr, input [7:0] addr, input [31:0] wd, output [31:0] rd);
    begin
      @(negedge clk); reg_cs = 1; reg_wr = wr; reg_addr = addr; reg_wdata = wd;
      @(posedge clk); #1; while (!reg_ack) begin @(posedge clk); #1; end
      rd = reg_rdata;
      @(negedge clk); reg_cs = 0; reg_wr = 0;
    end
  endtask

  task wb(input integer i, input wr, input [8:0] addr, input [31:0] wd, output [31:0] rd);
    begin
      @(negedge clk); wcyc[i] = 1; wstb[i] = 1; wwe[i] = wr; wadr[i] = addr; wdat[i] = wd;
      @(posedge clk); #1; while (!wack[i]) begin @(posedge clk); #1; end
      @(negedge clk); #5; rd = rdat[i];
      wcyc[i] = 0; wstb[i] = 0; wwe[i] = 0;
    end
  endtask

  // ---------------- test sequence ----------------
  integer cyc = 0, MAXC = 1000000, i, a, p, nbad, first, lastw;
  reg [31:0] s1, s2, d, pat;
  reg bad [0:511];
  initial void'($value$plusargs("MAXC=%d", MAXC));
  initial begin
    for (i = 0; i < 8; i = i + 1) begin wadr[i] = 0; wdat[i] = 0; end
    repeat (10) @(posedge clk); rst_n = 1;
    repeat (5) @(posedge clk);
    reg_access(1, 8'h0C, 32'h3333_3333, d);           // BIST_CTRL_2: en + run, all eight
    s1 = 0; s2 = 0;
    while (((s1 & 32'h0101_0101) != 32'h0101_0101 || (s2 & 32'h0101_0101) != 32'h0101_0101) && cyc < MAXC) begin
      repeat (100) @(posedge clk); cyc = cyc + 100;
      reg_access(0, 8'h10, 0, s1); reg_access(0, 8'h14, 0, s2);
    end
    repeat (20) @(posedge clk);
    reg_access(0, 8'h10, 0, s1); reg_access(0, 8'h14, 0, s2);
    $display("RESULT status1 %08h status2 %08h cycles %0d", s1, s2, cyc);
    dump = 1; #1;
    reg_access(1, 8'h0C, 32'h0, d);                   // functional mode
    for (i = 0; i < 8; i = i + 1) begin
      lastw = (i < 4) ? 507 : 251;
      for (a = 0; a <= lastw; a = a + 1) bad[a] = 0;
      for (p = 0; p < 3; p = p + 1) begin
        pat = (p == 1) ? 32'hFFFF_FFFF : 32'h0;
        for (a = 0; a <= lastw; a = a + 1) wb(i, 1, a, pat, d);
        for (a = 0; a <= lastw; a = a + 1) begin wb(i, 0, a, 0, d); if (d !== pat) bad[a] = 1; end
      end
      nbad = 0; first = -1;
      for (a = 0; a <= lastw; a = a + 1) if (bad[a]) begin nbad = nbad + 1; if (first < 0) first = a; end
      $display("RESULT inst %0d func_bad %0d first %0d", i, nbad, first);
    end
    $finish;
  end
endmodule
