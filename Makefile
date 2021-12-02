
all: libtest_objdump.pdf

%.dot: %.so
	python viz_disassemble.py -o $@ $<

%.pdf: %.dot
	dot -Tpdf -o $@ $<

clean:
	rm -f *.dot *.pdf