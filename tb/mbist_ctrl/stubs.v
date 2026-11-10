// Behavioural stand-ins for SkyWater std cells used by mbist_ctrl (no PDK needed).
module ctech_mux2x1 (input A0, input A1, input S, output X); assign X = S ? A1 : A0; endmodule
module ctech_buf (input A, output X); assign X = A; endmodule
module ctech_clk_buf (input A, output X); assign X = A; endmodule
module ctech_delay_buf (input A, output X); assign X = A; endmodule
// Clock-skew adjust cell chain (only feeds wbd_clk_mbist, not the MBIST core): pass-through.
module clk_skew_adjust (input clk_in, input [3:0] sel, output clk_out); assign clk_out = clk_in; endmodule
