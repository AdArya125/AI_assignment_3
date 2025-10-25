#!/usr/bin/env python3
import sys
from format_checker import parse_city

DIRS = ['L', 'R', 'U', 'D']
DIR_ID = {d: i for i, d in enumerate(DIRS)}

def var_id(k, x, y, d, N, M):
    return k * (N * M * 4) + (y * N + x) * 4 + DIR_ID[d] + 1

def parse_sat_output(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        raise ValueError("Empty satoutput file")
    if lines[0].startswith("UNSAT"):
        print("UNSAT — no model found.")
        return False, set()
    # handle both "SAT" and "SATISFIABLE"
    if not lines[0].startswith("SAT"):
        raise ValueError("Unexpected SAT output header: " + lines[0])
    vals = []
    for ln in lines[1:]:
        vals.extend(map(int, ln.split()))
    return True, set(v for v in vals if v > 0)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 debug_sat.py <basename>")
        sys.exit(1)

    base = sys.argv[1]
    city_file = base + ".city"
    sat_file = base + ".satoutput"

    spec = parse_city(city_file)
    N, M, K = spec.N, spec.M, spec.K
    sat, model = parse_sat_output(sat_file)
    if not sat:
        return

    print(f"=== Debugging SAT model for {base}.satoutput ===")
    print(f"Grid: {N}x{M}, Metro lines: {K}")
    print()

    for k in range(K):
        print(f"--- Metro line {k} ---")
        found = False
        for y in range(M):
            for x in range(N):
                active_dirs = []
                for d in DIRS:
                    vid = var_id(k, x, y, d, N, M)
                    if vid in model:
                        active_dirs.append(d)
                if active_dirs:
                    found = True
                    print(f"({x},{y}): {','.join(active_dirs)}")
        if not found:
            print("(no active cells)")
        print()

if __name__ == "__main__":
    main()
