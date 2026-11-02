# Top-level driver. Per-DUT cocotb makefiles live in tb/<dut>.mk once the top-level
# module and source list of each DUT are known (fill in after first compile).
DUT ?= tt777
SIM ?= icarus

.PHONY: sim faults mutants figs clean

sim:
	$(MAKE) -f tb/$(DUT).mk SIM=$(SIM)

faults:
	python campaigns/faults/run.py --dut $(DUT) --out results/faults_$(DUT).csv

mutants:
	python campaigns/mutants/run.py --dut $(DUT) --out results/mutants_$(DUT).csv

figs:
	for f in figs/plot_*.py; do python $$f; done

clean:
	rm -rf sim_build build results.xml *.vcd *.fst
