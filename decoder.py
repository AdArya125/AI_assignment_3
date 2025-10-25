from __future__ import print_function
import sys
from collections import namedtuple

MetroSpec = namedtuple(
    'MetroSpec', ['scenario', 'N', 'M', 'K', 'J', 'P', 'starts', 'ends', 'popular']
)


def parse_city(path):
    try:
        with open(path, 'r') as f:
            raw = [ln.rstrip('\n') for ln in f.readlines()]
    except Exception as e:
        raise ValueError("Failed reading city file %r: %s" % (path, e))

    if not raw:
        raise ValueError("Empty city file: %s" % path)
    i = 0
    while i < len(raw) and raw[i].strip() == '':
        i += 1
    if i >= len(raw):
        raise ValueError("City file contains only whitespace")
    first = raw[i].strip()
    if first not in ('1', '2'):
        raise ValueError(
            "First non-empty line must be '1' or '2' (scenario); got: %r" % first)
    scenario = int(first)
    i += 1
    while i < len(raw) and raw[i].strip() == '':
        i += 1
    if i >= len(raw):
        raise ValueError("Missing second line with grid params (N M K J [P])")
    params = raw[i].split()
    i += 1
    if scenario == 1:
        if len(params) != 4:
            raise ValueError(
                "Scenario 1 expects 4 ints on second line: N M K J")
        N, M, K, J = map(int, params)
        P = 0
    else:
        if len(params) != 5:
            raise ValueError(
                "Scenario 2 expects 5 ints on second line: N M K J P")
        N, M, K, J, P = map(int, params)
    if N <= 0 or M <= 0 or K < 0 or J < 0 or P < 0:
        raise ValueError("Invalid numeric values in header")
    starts = []
    ends = []
    for lineno in range(K):
        while i < len(raw) and raw[i].strip() == '':
            i += 1
        if i >= len(raw):
            raise ValueError(
                "Expected %d metro lines but file ended early" % K)
        toks = raw[i].split()
        i += 1
        if len(toks) != 4:
            raise ValueError(
                "Metro line %d: expected 4 integers (sx sy ex ey)" % lineno)
        sx, sy, ex, ey = map(int, toks)
        if not (0 <= sx < N and 0 <= ex < N and 0 <= sy < M and 0 <= ey < M):
            raise ValueError("Metro %d coordinates out of bounds: %r" %
                             (lineno, (sx, sy, ex, ey)))
        starts.append((sx, sy))
        ends.append((ex, ey))
    popular = []
    if scenario == 2:
        while i < len(raw) and raw[i].strip() == '':
            i += 1
        if i >= len(raw):
            raise ValueError("Scenario 2: missing line with popular cells")
        toks = raw[i].split()
        i += 1
        if len(toks) != 2 * P:
            raise ValueError(
                "Scenario 2: expected %d tokens for %d popular cells, got %d" % (2 * P, P, len(toks)))
        coords = list(map(int, toks))
        for pidx in range(P):
            x = coords[2 * pidx]
            y = coords[2 * pidx + 1]
            if not (0 <= x < N and 0 <= y < M):
                raise ValueError(
                    "Popular cell %d out of bounds: (%d,%d)" % (pidx, x, y))
            popular.append((x, y))
    if len(set(starts)) != len(starts):
        raise ValueError("Duplicate start locations in city file")
    if len(set(ends)) != len(ends):
        raise ValueError("Duplicate end locations in city file")
    if set(starts).intersection(set(ends)):
        raise ValueError(
            "Some start equals some end location (all starts & ends must be unique)")
    return MetroSpec(scenario=scenario, N=N, M=M, K=K, J=J, P=P, starts=starts, ends=ends, popular=popular)


def parse_sat_output(path, spec):
    try:
        with open(path, 'r') as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except Exception as e:
        raise ValueError("Failed reading SAT output %r: %s" % (path, e))

    if not lines:
        raise ValueError("Empty SAT output file")

    if lines[0].startswith("UNSAT"):
        return "UNSAT", []
    elif lines[0].startswith("SAT"):
        assignment = []
        if len(lines) > 1:
            assignment = [int(x) for x in lines[1].split() if x[0] != '-' and x != '0' and int(x) <= spec.K * spec.N * spec.M * 4]
        return "SAT", assignment
    else:
        raise ValueError("Invalid SAT output format")


def decode_solution(spec, assignment):
    # Map: (dx, dy) -> direction letter
    DIRS = {
        (1, 0): 'R',
        (-1, 0): 'L',
        (0, 1): 'D',
        (0, -1): 'U'
    }

    next_dir = {
        "R": (1, 0),
        "L": (-1, 0),
        "U": (0, -1),
        "D": (0, 1)
    }
    K = spec.K
    N = spec.N
    M = spec.M
    metro_rail_direction = ["L", "R", "U", "D"]

    # 1) Mapping Variables
    var_id = {}
    var_id_counter = 1
    for k in range(K):
        for x in range(N):
            for y in range(M):
                for cell_direction in metro_rail_direction:
                    var_id[var_id_counter] = (k, x, y, cell_direction)
                    var_id_counter += 1

    assignment_tuples = [var_id[val] for val in assignment]
    # print(assignment_tuples)
    line_assignments = {}

    for line, v1, v2, v3 in assignment_tuples:
        if line not in line_assignments:
            line_assignments[line] = []
        line_assignments[line].append((v1, v2, v3))
    # print(line_assignments)

    all_paths = []

    for line, points in line_assignments.items():
        # Build a quick lookup: (x,y) -> label
        # print(points)
        point_map = {(x, y): label for x, y, label in points}
        start = spec.starts[line]
        end = spec.ends[line]
        # print(point_map)
        point_map[end] = ""

        current = start
        visited = set([current])
        directions = []

        # Walk until we reach the end or no move is possible
        i = 0
        while (i < len(point_map)):
            # print(current)
            if current == end:
                # print("Broken at ",current,end)
                break

            x, y = current
            # print(point_map[current],"  ",next_dir[point_map[current]])
            nx, ny = next_dir[point_map[current]]
            directions.append(point_map[current])

            current = (x + nx, y + ny)
            i += 1

        all_paths.append(directions)

    return all_paths


def write_metromap(filename, metromap_lines):
    with open(filename, "w") as f:
        if metromap_lines == "UNSAT":
            f.write("0\n")
        else:
            for line in metromap_lines:
                f.write(" ".join(line) + " 0\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 decoder.py <basename>", file=sys.stderr)
        sys.exit(1)

    base = sys.argv[1]
    if(base.find(".city")!=-1):
        base=base[:-5]
    city_file = base + ".city"
    sat_file = base + ".satoutput"
    map_file = base + ".metromap"

    try:
        spec = parse_city(city_file)
        # print(spec)
        status, assignment = parse_sat_output(sat_file, spec)
        # print(status)
        # print("\n_________\n", assignment, "\n_________\n")  # debug print
    except Exception as e:
        print("Parsing error:", e, file=sys.stderr)
        sys.exit(1)

    if status == "UNSAT":
        write_metromap(map_file, "UNSAT")
        print("[Decoder] UNSAT → wrote '0' in metromap.")
        sys.exit(0)

    metromap = decode_solution(spec, assignment)
    write_metromap(map_file, metromap)
    print(f"[Decoder] Wrote metromap to {map_file}")


if __name__ == "__main__":
    main()
    # map_file="temp.metromap"
    # spec=MetroSpec(1,4,4,1,1,0,[(0,0)],[(3,3)],[])
    # metromap = decode_solution(spec,[2,18,34,52,56,60])
    # write_metromap(map_file, metromap)
    # print(f"[Decoder] Wrote metromap to {map_file}")