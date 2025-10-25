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


'''
Helper Functions
'''


def at_most_one(variables_for_cell):
    clauses_of_this_cell = set()
    length_of_variables = len(variables_for_cell)
    for i in range(length_of_variables):
        for j in range(i + 1, length_of_variables):
            clauses_of_this_cell.add((-variables_for_cell[i], -variables_for_cell[j]))
    return clauses_of_this_cell


def exactly_one(variables_for_cell):
    clauses = set()

    # At least One must be true
    clauses.add(tuple(variables_for_cell))

    # At most one must be true
    length = len(variables_for_cell)
    for i in range(length):
        for j in range(i + 1, length):
            clauses.add((-variables_for_cell[i], -variables_for_cell[j]))
    return clauses

def at_most_J_turns(vars_list, J):
    clauses = set()
    n = len(vars_list)
    if n <= J:
        return clauses
    if J == 0:
        for v in vars_list:
            clauses.add((-v,))
        return clauses
    aux = {}
    base_aux = max(vars_list) + 1
    for i in range(n):
        for j in range(J):
            aux[(i, j)] = base_aux
            base_aux += 1
    for i in range(n):
        v = vars_list[i]
        for j in range(J):
            if i == 0 and j == 0:
                clauses.add((-v, aux[(i, j)]))
            elif i == 0:
                clauses.add((-aux[(i, j)],))
            elif j == 0:
                clauses.add((-v, aux[(i, j)]))
                clauses.add((-aux[(i - 1, j)], aux[(i, j)]))
            else:
                clauses.add((-v, -aux[(i - 1, j - 1)], aux[(i, j)]))
                clauses.add((-aux[(i - 1, j)], aux[(i, j)]))
    for i in range(n):
        clauses.add((-aux[(i, J - 1)],))
    return clauses, base_aux - 1


def encode_to_sat(spec):
    clauses = set()
    K = spec.K
    N = spec.N
    M = spec.M
    J = spec.J
    metro_rail_direction = ["L", "R", "U", "D"]

    # 1) Mapping Variables
    '''
    Number of variable generated : K * N * M * 4
    '''
    var_id = {}
    var_id_counter = 1
    for k in range(K):
        for x in range(N):
            for y in range(M):
                for cell_direction in metro_rail_direction:
                    var_id[(k, x, y, cell_direction)] = var_id_counter
                    var_id_counter += 1

    print("Variable Generated")
    for k in range(K):
        turns_list = []
        for x in range(N):
            for y in range(M):
                var_id[(k, x, y)] = var_id_counter
                turns_list.append(var_id_counter)
                var_id_counter += 1
        turn_clauses, new_max_var = at_most_J_turns(turns_list, J)
        clauses |= turn_clauses
        var_id_counter = max(var_id_counter, new_max_var + 1)

    print("At most turns clauses Added")

    # 2) At most one rail direction per cell
    '''
    Number of Clauses generated : 6 * K * N * M
    6 per cell.
    '''
    for k in range(K):
        for x in range(N):
            for y in range(M):
                possible_direction_for_this_cell = []
                for cell_direction in metro_rail_direction:
                    possible_direction_for_this_cell.append(var_id[(k, x, y, cell_direction)])
                clauses_for_this_cell = at_most_one(possible_direction_for_this_cell)
                clauses = clauses | clauses_for_this_cell
    print("At most one rail per cell clauses Added")
    # print(len(clauses))

    # 3) Every edge cannot have one direction
    '''
    Number of Clauses generated : ((2 * 4) + (N - 2) * 2 + (M - 2) * 2) * K
    1) every corner cannot have 2 directions
    2) every edge cannot have 1 directions
    '''
    # old_clauses=clauses
    # clauses=set()
    for k in range(K):
        for x in range(N):
            for y in range(M):
                if x == 0:  # Left Column
                    clauses.add((-var_id[(k, x, y, "L")]))
                if x == N - 1:  # Right Column
                    clauses.add((-var_id[(k, x, y, "R")]))
                if y == 0:  # Top Row
                    clauses.add((-var_id[(k, x, y, "U")]))
                if y == M - 1:  # Bottom Row
                    clauses.add((-var_id[(k, x, y, "D")]))
    # print(len(clauses),"\n",clauses)
    print("Edge/corner clauses added")

    # 4) Giving Start a valid direction and End no direction
    '''
    K * 4 <= Number of Clauses generated  <= K * 2 * 4 
    1) minimum is when all endpoints are on corners
    2) maximum is when all endpoints are internal
    '''
    start_points = []
    end_points = []
    valid_starting_direction = []
    opposites = {
        "L": "R",
        "R": "L",
        "U": "D",
        "D": "U"
    }
    neighbors = {
        "L": (-1, 0),
        "R": (1, 0),
        "U": (0, -1),
        "D": (0, 1)
    }
    # old_clauses=clauses
    # clauses=set()

    for k in range(K):
        sx, sy = spec.starts[k]
        ex, ey = spec.ends[k]
        start_points.append((sx, sy))
        end_points.append((ex, ey))
        kth_starting_valid_directions = []
        variable_for_cell = []
        clauses.add((-var_id[(k, sx, sy)], ))
        # Giving Start point a valid direction
        for cell_direction in metro_rail_direction:
            v = var_id[(k, sx, sy, cell_direction)]
            (dx, dy) = neighbors[cell_direction]
            nx, ny = sx + dx, sy + dy
            # print(f"{cell_direction} -> ({dx}, {dy}) new cell -> ({nx}, {ny})")
            # OUT OF BOUNDS
            if not (0 <= nx < N and 0 <= ny < M):
                continue
            variable_for_cell.append(v)
            kth_starting_valid_directions.append(cell_direction)
        # print(f"For starting point ({sx, sy}) its clauses are : ", exactly_one(variable_for_cell))
        clauses = clauses | exactly_one(variable_for_cell)
        valid_starting_direction.append(kth_starting_valid_directions)

        # Giving Ending Point no Direction
        clauses.add((-var_id[(k, ex, ey)],))
        for cell_direction in metro_rail_direction:
            v = var_id[(k, ex, ey, cell_direction)]
            clauses.add((-v, ))

    # print(len(clauses),"\n",clauses)
    # clauses=clauses | old_clauses

    # print(valid_starting_direction)
    print("Gave start and end their respective direction")

    # 5) Make sure Start has valid neighbors
    for k in range(K):
        sx, sy = spec.starts[k]
        ex, ey = spec.ends[k]
        kth_starting_valid_directions = valid_starting_direction[k]
        for starting_direction in kth_starting_valid_directions:
            v = var_id[(k, sx, sy, starting_direction)]
            (dx, dy) = neighbors[starting_direction]
            nx, ny = sx + dx, sy + dy
            if (nx, ny) == (ex, ey):
                continue
            local = []
            for cell_direction in metro_rail_direction:
                if cell_direction != opposites[starting_direction]:
                    # print(f"For ({sx}, {sy}) and its direction {starting_direction} neighbor has direction option {cell_direction}")
                    local.append(var_id[k, nx, ny, cell_direction])
            clauses.add(tuple([-v] + local))
    print("Added clause to give start its neighbor")
    # print(len(clauses))

    # 6) Incoming Edge to an End
    # old_clauses=clauses
    # clauses=set()

    for k in range(K):
        ex, ey = spec.ends[k]
        variable_for_cell = []
        for neighbor in neighbors:
            (dx, dy) = neighbors[neighbor]
            nx, ny = ex + dx, ey + dy
            if not (0 <= nx < N and 0 <= ny < M):
                continue
            # print(f"For ({ex, ey}) neighbor on {nx, ny} is {opposites[neighbor]}")
            variable_for_cell.append((var_id[(k, nx, ny, opposites[neighbor])]))
        # print(f"For End ({ex, ey}) its clauses are : ", exactly_one(variable_for_cell))
        clauses = clauses | exactly_one(variable_for_cell)
    # print(end_points, start_points)
    print("Added clause to give end an incoming edge")
    # print(len(clauses),"\n",clauses)
    # clauses=clauses | old_clauses

    # 6.5) start's valid neighbors should'nt point towards it
    for k in range(K):
        sx, sy = spec.starts[k]
        variable_for_cell = []
        for neighbor in neighbors:
            (dx, dy) = neighbors[neighbor]
            nx, ny = sx + dx, sy + dy
            if not (0 <= nx < N and 0 <= ny < M):
                continue
            # print(f"For ({ex, ey}) neighbor on {nx, ny} is {opposites[neighbor]}")
            variable_for_cell.append((-var_id[(k, nx, ny, opposites[neighbor])]))
        # print(f"For End ({ex, ey}) its clauses are : ", exactly_one(variable_for_cell))
        clauses = clauses | set(tuple([var]) for var in variable_for_cell)

    print("Starting to add directions")
    # print("start conditions:\n",set([tuple([var]) for var in variable_for_cell]))
    # 7) If an edge is pointing towards an empty neighbor then it must be END otherwise it has to connect
    # old_clauses=clauses
    # clauses=set()
    for k in range(K):
        print("Calculating for metro ", k+1)
        for x in range(N):
            for y in range(M):
                if (x, y) in end_points:
                    continue

                for cell_direction in metro_rail_direction:
                    local = []
                    (dx, dy) = neighbors[cell_direction]
                    nx, ny = x + dx, y + dy
                    # OUT OF BOUNDS
                    # if (nx,ny) in start_points + end_points: continue
                    if not (0 <= nx < spec.N and 0 <= ny < spec.M):
                        # clauses.add(tuple([-var_id[(k,x,y,cell_direction)]]))
                        continue

                    if (nx, ny) != spec.starts[k] and (nx, ny) != spec.ends[k]:
                        next_cell_possible_turns = []
                        for next_cell_direction in metro_rail_direction:
                            if next_cell_direction != opposites[cell_direction]:
                                if next_cell_direction != cell_direction:
                                    next_cell_possible_turns.append(-var_id[(k, nx, ny, next_cell_direction)])
                                local.append(var_id[(k, nx, ny, next_cell_direction)])
                        clauses.add(tuple([-var_id[(k, x, y, cell_direction)]] + local))
                        print(tuple([-var_id[(k, x, y, cell_direction)]] + local))
                        for next_cell_possible_turn in next_cell_possible_turns:
                            clauses.add(
                                tuple([-var_id[(k, x, y, cell_direction)]] + [next_cell_possible_turn] + [var_id[k, nx, ny]])
                            )
                            print(tuple([-var_id[(k, x, y, cell_direction)]] + [next_cell_possible_turn] + [var_id[k, nx, ny]]))
                        # print(var_id[(k, x, y, cell_direction)], next_cell_possible_turns)
                        vars = []
                        for d in metro_rail_direction:
                            if d == cell_direction:
                                # print("direction ",d)
                                continue

                            tx, ty = neighbors[d]
                            tx += x
                            ty += y
                            if (0 <= tx < spec.N and 0 <= ty < spec.M):
                                vars.append(var_id[(k, tx, ty, opposites[d])])
                                
                        
                        if(x,y) not in start_points and (x,y) not in end_points:
                            print(var_id[(k,x,y,cell_direction)],vars)
                            clauses = clauses | at_most_one(vars)
    print("Ending adding directions")

    # print("Debug :",len(clauses), "\n_________\n",clauses )
    # clauses=clauses|old_clauses

    def valid_coordinates(x, y):
        if (0 <= x < spec.N and 0 <= y < spec.M):
            return True
        return False

    # temp=[]
    for k in range(K):
        (ex, ey) = spec.ends[k]
        n = []
        for side in neighbors:
            dx, dy = neighbors[side]
            if valid_coordinates(ex + dx, ey + dy):
                n.append(side)
        for k1 in range(K):
            if k1 == k: continue

            for val in metro_rail_direction:
                clauses.add((-var_id[(k1, ex, ey, val)]))
            for side in n:
                dx, dy = neighbors[side]
                # temp.append((-var_id[(k1,ex+dx,ey+dy,opposites[side])]))
                clauses.add((-var_id[(k1, ex, ey, opposites[side])]))

        # print(n)
        # print(temp)

    # 8) No Metro lines must overlap
    for x in range(spec.N):
        for y in range(spec.M):
            clauses_for_this_cell = []
            for k in range(spec.K):
                for cell_direction in metro_rail_direction:
                    clauses_for_this_cell.append(var_id[(k, x, y, cell_direction)])
            clauses = clauses | at_most_one(clauses_for_this_cell)
    # print(len(clauses))

    
    # 9) P!!
    if(spec.scenario==2):    
        l=[]
        for (px,py) in spec.popular:
            for k in range(K):
                for direction in metro_rail_direction:
                    l.append(var_id[(k,px,py,direction)])
            clauses|= exactly_one(l)

    num_vars = var_id_counter - 1
    return num_vars, clauses


def write_cnf(filename, num_vars, clauses):
    """
    Write CNF in DIMACS format.
    Works whether `clauses` is a list or set, and whether each element
    is a tuple, list, or single-literal int.
    """
    with open(filename, "w") as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for clause in clauses:
            # Normalize to an iterable of ints
            if isinstance(clause, int):
                lits = [clause]
            elif isinstance(clause, (tuple, list, set)):
                lits = list(clause)
            else:
                continue  # skip malformed
            f.write(" ".join(map(str, lits)) + " 0\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 encoder.py <basename>", file=sys.stderr)
        sys.exit(1)

    base = sys.argv[1]
    if(base.find(".city")!=-1):
        base=base[:-5]
    
    city_file = base + ".city"
    sat_file = base + ".satinput"

    try:
        spec = parse_city(city_file)
    except Exception as e:
        print("City parse error:", e, file=sys.stderr)
        sys.exit(1)

    num_vars, clauses = encode_to_sat(spec)
    write_cnf(sat_file, num_vars, clauses)

    print(f"[Encoder] Successfully wrote {sat_file}")
    print(f"Variables: {num_vars}, Clauses: {len(clauses)}")


if __name__ == "__main__":
    main()