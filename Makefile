export TARGET

install:
	ln -s $(shell pwd)/simple-serial.sh /usr/bin/simple-serial
	ln -s $(shell pwd)/armock/armock.sh /usr/bin/armock

uninstall:
	rm /usr/bin/simple-serial
	rm /usr/bin/armock

install-dev:
	python3 -m pip install --user pyserial nose rednose
	sudo dnf install inotify-tools ShellCheck

lint:
	shellcheck simple-serial.sh
	shellcheck armock/armock.sh

test-arterm: TARGET=armock
test-arterm: SUITE=EEPROM InvalidPinModes PinsSim Serial ShmClearing Time
test-arterm: test/armock nose

test-arterm-nano: TARGET=nano
test-arterm-nano: SUITE=Serial Time
test-arterm-nano: nose

test-arterm-fixture: TARGET=nano-fixture
test-arterm-fixture: SUITE=Serial Time PinsFixture
test-arterm-fixture: nose

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

watch:
	while true; do make $(ARGS); inotifywait --event modify $(FILE); done
