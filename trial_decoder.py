from collections import namedtuple
import sys

MetroSpec = namedtuple(
        'MetroSpec', ['scenario', 'N', 'M', 'K', 'J', 'P', 'starts', 'ends', 'popular']
    )

def decode(spec):
    positive_vars = [7, 41, 81, 123, 132, 142, 159, 197, 231, 260, 262, 275]

    metro_rail_dir = ["H", "V", "TR", "TL", "BR", "BL", "ER", "EL", "EU", "ED"]
    var_id = {}
    var_id_counter = 1

    # Step 1: Variable mapping
    for k in range(spec.K):
        for x in range(spec.N):
            for y in range(spec.M):
                for d in metro_rail_dir:
                    var_id[var_id_counter] = (k, x, y, d)
                    var_id_counter += 1
    n = spec.N
    m = spec.M
    for var in positive_vars:
        metro_line = ((var - 1) // (n * m * 10))
        cell_no = (var - metro_line * n * m * 10) // 10 + 1
        y = (cell_no - 1) % n
        x = (cell_no - 1) // n
        d = metro_rail_dir[(var - 1) % 10]
        print("POSITIVE VAR ARE : ", var_id[var], "ITS ID is ", var, "Calculated : ", (metro_line, x, y, d), "Cell no : ", cell_no)


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

def main():

    base = "Assets/1_4/4_4_1"
    city_file = base + ".city"
    sat_file = base + ".satinput"

    try:
        spec = parse_city(city_file)
        decode(spec)
    except Exception as e:
        print("City parse error:", e, file=sys.stderr)
        sys.exit(1)



if __name__ == "__main__":
    main()