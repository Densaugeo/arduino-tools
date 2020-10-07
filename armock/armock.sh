#!/bin/bash
set -euf -o pipefail

if [[ $# == 0 || $# -gt 2 || $1 == "help" ]]; then
  echo "Usage: armock SKETCH [PTY]";
  echo "To look at pins: xxd /dev/shm/armock_pins";
  echo "To set pin 2 = 7: echo '2: 07' | xxd -r - /dev/shm/armock_pins";
  exit;
fi

# Canonicalize = recursive
SKETCH=$(readlink --canonicalize "$1")
if [[ $# == 2 ]]; then PTY=$(readlink --canonicalize "$2"); fi
cd "$(dirname "$(readlink --canonicalize "$0")")"

echo "Compiling armock.cpp with $SKETCH..."
# -lrt option is required for mmap()
g++ armock.cpp -o armock -lrt -D SKETCH="\"$SKETCH\"" -I .

if [[ $# == 1 ]]; then
  echo "Starting armock...";
  ./armock;
else
  echo "Starting armock with serial io connected to $PTY...";
  socat exec:./armock,pty,raw,echo=0 pty,raw,echo=0,link="$PTY";
fi
