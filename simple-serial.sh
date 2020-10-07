#!/bin/bash
set -euf -o pipefail

if [[ $# != 1 || $1 == "help" ]]; then
  echo "Usage: simple-serial TTY";
  exit;
fi

function cleanup {
  if [ "$CAT_PID"    ]; then kill "$CAT_PID"   ; fi
}

trap cleanup EXIT

stty -F "$1" 115200 raw

# Disable various problematic serial options. Because different distros support different options, some stty calls may error out, so errors are suppressed
set +e
stty -F "$1" -echo 2> /dev/null
stty -F "$1" -echoe 2> /dev/null
stty -F "$1" -echok 2> /dev/null
stty -F "$1" -echoke 2> /dev/null
stty -F "$1" -echoctl 2> /dev/null
stty -F "$1" -onlcr 2> /dev/null
set -e

cat < "$1" &
CAT_PID=$!

# -r causes read to not interpret escapes and pass \ through
# -e causes echo to interpret escape sequences
while read -r LINE; do echo "$LINE" > "$1"; done
