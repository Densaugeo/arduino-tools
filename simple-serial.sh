#!/bin/bash
set -euf -o pipefail

BAUD_RATE=115200 # Default
LINE_ENDING="\n" # Default
USAGE="Usage: simple-serial [--baud 9600] [--line-ending '\r\n'] TTY"

# Apply abbreviations for options
for ARG in "$@"; do
  shift
  case "$ARG" in
    "--help") set -- "$@" "-h" ;;
    "--baud") set -- "$@" "-b" ;;
    "--line-ending") set -- "$@" "-l" ;;
    *) set -- "$@" "$ARG"
  esac
done

# Parse options
while getopts "hb:l:" OPT; do
  case "$OPT" in
    "h") echo "$USAGE"; exit ;;
    "b") BAUD_RATE="$OPTARG" ;;
    "l") LINE_ENDING="$OPTARG" ;;
    "?") ;;
  esac
done
shift $((OPTIND - 1)) # Remove parsed options

# After parsing, the only argument remaining should be TTY
if [[ $# != 1 ]]; then echo "$USAGE"; exit; fi

stty -F "$1" "$BAUD_RATE" raw

# Disable various problematic serial options. Because different distros support different options, some stty calls may error out, so errors are suppressed
set +e
stty -F "$1" -echo 2> /dev/null
stty -F "$1" -echoe 2> /dev/null
stty -F "$1" -echok 2> /dev/null
stty -F "$1" -echoke 2> /dev/null
stty -F "$1" -echoctl 2> /dev/null
stty -F "$1" -onlcr 2> /dev/null
set -e

function cleanup {
  if [ "$CAT_PID" ]; then kill "$CAT_PID"; fi
}

trap cleanup EXIT

cat < "$1" &
CAT_PID=$!

# -r causes read to not interpret escapes and pass \ through
# -e causes echo to interpret escape sequences
# -n causes echo to not add \n
while read -r LINE; do echo -en "$LINE$LINE_ENDING" > "$1"; done
