export TARGET=sim
SUITE=test/arterm.py

install-dev:
	python3 -m pip install --user pyserial nose rednose
	sudo dnf install ShellCheck

test-armock: test/arterm.py test/armock
	python3 -m nose --verbosity=2 --rednose $(SUITE)

test-armock-pretty: test/arterm.py test/armock
	python3 -u -m nose --verbosity=2 --rednose --force-color $(SUITE) 2>&1 | gawk -f test/pretty-printer.awk

test-nano: TARGET=nano
test-nano: SUITE=test/arterm.py:Serial test/arterm.py:Time
test-nano: test/arterm.py
	python3 -m nose --verbosity=2 --rednose $(SUITE)

test-nano-pretty: TARGET=nano
test-nano-pretty: SUITE=test/arterm.py:Serial test/arterm.py:Time
test-nano-pretty: test/arterm.py
	python3 -u -m nose --verbosity=2 --rednose --force-color $(SUITE) 2>&1 | gawk -f test/pretty-printer.awk

test/armock: armock/armock.cpp arterm/arterm.ino
	g++ armock/armock.cpp -o test/armock -lrt -D SKETCH='"../arterm/arterm.ino"' -I armock

clean:
	rm -rf test/armock armock/armock-quick-sim test/pty-master test/pty-slave test/__pycache__
