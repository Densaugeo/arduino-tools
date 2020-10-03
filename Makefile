SUITE=test/arterm.py

install-dev:
	python3 -m pip install --user pyserial nose rednose
	sudo dnf install ShellCheck

test-armock: test/arterm.py test/armock
	python3 -m nose --verbosity=2 --rednose $(SUITE)

test-armock-pretty: test/arterm.py test/armock
	python3 -u -m nose --verbosity=2 --rednose --force-color $(SUITE) 2>&1 | gawk -f test/pretty-printer.awk

test/armock: armock/armock.cpp arterm/arterm.ino
	g++ armock/armock.cpp -o test/armock -lrt -D SKETCH='"arterm/arterm.ino"'

clean:
	rm -rf test/armock test/pty-master test/pty-slave test/__pycache__
