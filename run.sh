#!/bin/bash
# run.sh
# Usage: ./run.sh <basename or path>

if [ -z "$1" ]; then
  echo "Usage: $0 <basename>"
  exit 1
fi

BASENAME="$1"
CNF_FILE="${BASENAME}.satinput"   # Encoder should create this
OUT_FILE="${BASENAME}.satoutput"   # Minisat will write here

# 1. Run encoder
./run1.sh "$BASENAME"

# 2. Run minisat
minisat "$CNF_FILE" "$OUT_FILE"
# > /dev/null 2>&1

# 3. Run decoder
./run2.sh "$BASENAME"

python3 format_checker.py "$BASENAME"

python3 visualize3.py "$BASENAME"