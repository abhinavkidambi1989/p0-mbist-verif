# #777 smoke-test observations (2 Nov 2026)

Design: Tiny Tapeout IHP 26a #777, `adityapundir1985/tt_um_aksp_mbist_mbisr` @ 94fb5aa (Apache-2.0).
Testbench: `tb/tt777/tb_tt777.v` (behavioural stuck-at injection, no RTL edits). Raw output: `results/tt777_smoke.txt`.
Status: observed in simulation by Claude; **Abhinav to review and confirm in waveforms before using in the paper.**

| # | Observation | Evidence |
|---|---|---|
| O1 | Reported `fail_addr` is off by one: fault at A reported as A-1 in descending elements, A+1 in ascending ones. The read check uses `read_addr` after it has already moved on. | T1: fault @5 -> fail_addr 4. T3: fault @12 -> 13, 12, 13 |
| O2 | **Escape:** stuck-at-0 at address 0 is never detected (DONE=1, FAIL=0 on a faulty memory). The last read of ↓(r1,w0) at address 0 is never checked, and it is the only r1 element in the shortened March C-. | T5 |
| O3 | One failure fills **every** free repair entry with the same address (non-blocking `inserted` flag read in the same cycle). | T1: repair[0]=repair[1]=4 |
| O4 | With two faulty cells only one address is recorded; the second is dropped because the table is already full of duplicates. | T2: faults @5,@9 -> both entries = 8 |
| O5 | Repair entries store the wrong (off-by-one) address, so repair would remap a good cell and leave the faulty one in use. | O1 + O3 |
| O6 | Spare rows (0x1E–0x1F) are inside the normal tested address range, so a "spare" is also a user cell; a fault at 30 is "repaired" by remapping 29 onto the faulty cell 30. | T4 |
| O7 | Documentation says 256x8 memory and 16 repair entries; RTL is 32x8 with MAX_REPAIRS=2. | `top.v` parameters vs. project page |
| O8 | Algorithm is a 4-element shortened March C- (↕w0; ↑(r0,w1); ↓(r1,w0); ↑r0), not full 6-element March C- (missing ↑(r1,w0), ↓(r0,w1)). | `mbist_marchc_controller.v` |

Key point for the paper: the design's own cocotb test only waits for DONE, so it passes with every one of these issues present.
