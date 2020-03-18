#!/bin/bash
set -e

if [[ ! $1 || $1 == "help" ]]; then
  echo "Usage: quick-sim.sh SKETCH";
  echo "To look at pins: xxd /dev/shm/armock_pins";
  echo "To set pin 2 = 7: echo '2: 07' | xxd -r - /dev/shm/armock_pins";
  exit;
fi

echo "Compiling armock.cpp with $1..."
g++ armock.cpp -o armock-quick-sim -lrt -D SKETCH="\"$1\""
# -lrt option is required for mmap()

function cleanup {
  set +e

  if [ $ARMOCK_PID ]; then kill $ARMOCK_PID; fi
  if [ $CAT_PID    ]; then kill $CAT_PID   ; fi
  if [ $SOCAT_PID  ]; then kill $SOCAT_PID ; fi
}

trap cleanup EXIT

echo "Creating pty-slave and pty-master..."
socat pty,raw,echo=0,link=pty-slave pty,raw,echo=0,link=pty-master &
SOCAT_PID=$!

sleep 1

echo "Starting armock attached to pty-slave..."
./armock-quick-sim pty-slave &
ARMOCK_PID=$!

echo "Relaying this terminal to pty-master..."
cat < pty-master &
CAT_PID=$!

echo "Ready"

while read -r LINE; do echo "$LINE" > pty-master; done
# -r causes read to not interpret escapes and pass \ through
# -e causes echo to interpret escape sequences
