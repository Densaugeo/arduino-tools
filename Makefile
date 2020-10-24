export TARGET

install:
	ln -s $(shell pwd)/simple-serial.sh /usr/bin/simple-serial
	ln -s $(shell pwd)/armock/armock.sh /usr/bin/armock

uninstall:
	rm /usr/bin/simple-serial
	rm /usr/bin/armock

install-dev:
	python3 -m pip install --user pyserial nose rednose
	sudo dnf install ShellCheck

lint:
	shellcheck simple-serial.sh
	shellcheck armock/armock.sh

test-armock: TARGET=sim
test-armock: SUITE=EEPROM InvalidPinModes PinsSim Serial ShmClearing Time
test-armock: nose test/armock

test-nano: TARGET=nano
test-nano: SUITE=PinsFixture Serial Time
test-nano: nose

test/armock: armock/armock.cpp arterm/arterm.ino
	g++ armock/armock.cpp -o test/armock -lrt -D SKETCH='"../arterm/arterm.ino"' -I armock

nose: test/arterm.py
ifndef PRETTY
	python3 -m nose --verbosity=2 --rednose $(addprefix test/arterm.py:,$(SUITE))
else
	python3 -u -m nose --verbosity=2 --rednose --force-color $(addprefix test/arterm.py:,$(SUITE)) 2>&1 | gawk -f test/pretty-printer.awk
endif

clean:
	rm -rf test/armock armock/armock test/__pycache__
