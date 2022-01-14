export TARGET

install:
	ln -s $(shell pwd)/simple-serial.sh /usr/bin/simple-serial
	ln -s $(shell pwd)/armock/armock.sh /usr/bin/armock

uninstall:
	rm /usr/bin/simple-serial
	rm /usr/bin/armock

install-dev:
	python3 -m pip install --user pyserial pytest
	sudo dnf install inotify-tools ShellCheck
	arduino-cli core update-index
	arduino-cli core install arduino-avr

lint:
	shellcheck simple-serial.sh
	shellcheck armock/armock.sh

test-arterm: TARGET=armock
test-arterm: SUITE=EEPROM or InvalidPinModes or PinsSim or Serial or ShmClearing or Time
test-arterm: test/armock pytest

test-arterm-nano: TARGET=nano
test-arterm-nano: SUITE=Serial or Time
test-arterm-nano: pytest

test-arterm-fixture: TARGET=nano-fixture
test-arterm-fixture: SUITE=Serial or Time or PinsFixture
test-arterm-fixture: pytest

test/armock: armock/armock.cpp arterm/arterm.ino
	g++ armock/armock.cpp -o test/armock -lrt -D SKETCH='"../arterm/arterm.ino"' -I armock

pytest: test/arterm.py
ifndef PRETTY
	python3 -m pytest -v -k '$(SUITE)' test/arterm.py
else
	python3 -u -m pytest -v --color yes -k '$(SUITE)' test/arterm.py 2>&1 | gawk -f test/pretty-printer.awk
endif

upload: arterm/arterm.ino
ifndef PORT
	# PORT must be specified
else
	arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328old arterm/arterm.ino
	arduino-cli upload --port $(PORT) --fqbn arduino:avr:nano:cpu=atmega328old arterm/arterm.ino
endif

clean:
	rm -rf test/armock armock/armock test/__pycache__

watch:
	while true; do make $(ARGS); inotifywait --event modify $(FILE); done
