PYTHON = python
tests := $(wildcard *.py)

all: $(tests)
	for test in $(tests); do\
		PYTHONPATH=../.. $(PYTHON) $${test};\
	done
