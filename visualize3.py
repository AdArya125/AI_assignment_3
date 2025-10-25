import sys
import matplotlib.pyplot as plt
from collections import namedtuple

# Direction vectors for each move character
MOVE = {
    'U': (0, -1),
    'D': (0, 1),
    'L': (-1, 0),
    'R': (1, 0)
}

MetroSpec = namedtuple(
    'MetroSpec', ['scenario', 'N', 'M', 'K', 'J', 'P', 'starts', 'ends', 'popular']
)

def parse_city(path):
    """
    Parses the .city file and returns a MetroSpec.
    """
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

def get_assignments(path):
    """
    Reads the SAT output file and returns positive variable assignments.
    """
    try:
        with open(path, 'r') as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except Exception as e:
        raise ValueError("Failed reading SAT output %r: %s" % (path, e))

    if not lines:
        raise ValueError("Empty SAT output file")

    if lines[0].startswith("UNSAT"):
        return []
    elif lines[0].startswith("SAT"):
        assignment = []
        if len(lines) > 1:
            assignment = [int(x) for x in lines[1].split() if x[0] != '-' and x != '0']
        return assignment
    else:
        return []

def decode_to_grid(spec, positive_vars):
    """
    Decodes positive SAT variables into a 2D grid representation.
    """
    metro_rail_direction = ["L", "R", "U", "D"]
    var_id = {}
    var_id_counter = 1
    
    for k in range(spec.K):
        for x in range(spec.N):
            for y in range(spec.M):
                for cell_direction in metro_rail_direction:
                    var_id[var_id_counter]=(k, x, y, cell_direction)
                    var_id_counter += 1
    
    n = spec.N
    m = spec.M
    grid = [['.' for _ in range(n)] for _ in range(m)]
    # check_k=3
    for var in positive_vars:
        if var in var_id:
            k, x, y, d = var_id[var]
            # if(k!=check_k): continue
            grid[y][x] = f"{k+1}:{d}"
    
    for k in range(spec.K):
        # if(k!=check_k): continue
        sx,sy=spec.starts[k]
        ex,ey=spec.ends[k]
        
        grid[sy][sx]=f"| S{k+1} | "+grid[sy][sx]+ ' |'
        grid[ey][ex]=f"| E{k+1} | "+grid[ey][ex]+ ' |'
        
        
    return grid

def plot_grid(ax, grid):
    """
    Plots the decoded grid on the given axes.
    """
    n_rows = len(grid)
    n_cols = len(grid[0]) if n_rows > 0 else 0

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)

    # Draw grid
    for x in range(n_cols + 1):
        ax.axvline(x, color='black', linewidth=1)
    for y in range(n_rows + 1):
        ax.axvline(y, color='black', linewidth=1)
        ax.hlines(y, 0, n_cols, color='black', linewidth=1)

    # Place each value at the center of its cell
    for i in range(n_rows):
        for j in range(n_cols):
            ax.text(j + 0.5, n_rows - 1 - i + 0.5, grid[i][j],
                    va='center', ha='center', fontsize=8)

    ax.axis('off')
    # ax.invert_yaxis()
    ax.set_title("SAT Variable Assignment Grid")

def read_metromap_file(metromap_path):
    """
    Reads the .metromap file and extracts metro paths.
    """
    try:
        with open(metromap_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except:
        return None

    if not lines or (len(lines) == 1 and lines[0] == '0'):
        return None

    paths = []
    for line in lines:
        print(line)
        parts = line.split()
        if parts[-1] == '0':
            parts = parts[:-1]
        paths.append(parts)
    return paths

def reconstruct_path(start, directions):
    """
    Reconstructs the path from start position using direction strings.
    """
    x, y = start
    path_points = [(x, y)]
    for d in directions:
        dx, dy = MOVE[d]
        x += dx
        y += dy
        path_points.append((x, y))
    return path_points

def plot_metrolines(ax, base_name, spec, metro_paths):
    """
    Plots the metro lines on the given axes.
    """
    N, M = spec.N, spec.M
    if(metro_paths is None): 
        metro_paths=[]
        
        ax.text(0.95, 0.95, f'UNSAT', transform=ax.transAxes,bbox=dict(facecolor='red', alpha=0.6), ha='right', va='top',fontsize=9, weight = "bold",color="w")
    else:
        ax.text(0.95, 0.95, f'SAT', transform=ax.transAxes,bbox=dict(facecolor='green', alpha=0.6), ha='right', va='top',fontsize=9, weight = "bold",color="w")
    # Draw grid
    for x in range(N + 1):
        ax.axvline(x, color='lightgray', linewidth=0.7)
    for y in range(M + 1):
        ax.axhline(y, color='lightgray', linewidth=0.7)

    colors = ["red", "blue", "green", "purple", "orange", "brown", "black", "pink"]
    ax.text(0.05, 0.95, f'| N: {spec.N} | M: {spec.M} | K: {spec.K} | J: {spec.J} | P: {spec.P} |', transform=ax.transAxes,bbox=dict(facecolor='blue', alpha=0.5), ha='left', va='top',fontsize=9, weight = "bold",color="w")
    
    
    for i,(sx,sy) in enumerate(spec.starts):       # Start points
        ax.scatter(sx, sy, s=80, color="blue")
        ax.text(sx, sy, f"S{i+1}", color="blue", fontsize=9, ha="right", va="bottom", weight='bold')
    
    for i,(ex,ey) in enumerate(spec.ends):       # End points
        ax.scatter(ex, ey, s=80, color="red")
        ax.text(ex, ey, f"E{i+1}", color="red", fontsize=9, ha="right", va="bottom", weight='bold')
        
    for i,(px,py) in enumerate(spec.popular):       # Popular points
        ax.scatter(px, py, s=80, color="cyan")
        ax.text(px, py, f"P{i+1}", color="cyan", fontsize=9, ha="right", va="bottom", weight='bold')

    for i, dirs in enumerate(metro_paths):
        
        x1, y1 = spec.starts[i]
        x2, y2 = spec.ends[i]
        i+=1
        path_points = reconstruct_path((x1, y1), dirs)

        xs = [p[0] for p in path_points]
        ys = [p[1] for p in path_points]
        color = colors[i % len(colors)]

        # Draw path
        ax.plot(xs, ys, marker='o', color=color, label=f"Line {i}")

        # # Mark start point
        # ax.scatter(x1, y1, s=100, color="blue")
        # ax.text(x1, y1, f"S{i}", color="blue", fontsize=9, ha="right", va="bottom", weight='bold')

        # # Mark end point
        # ax.scatter(x2, y2, s=100, color="red")
        # ax.text(x2, y2, f"E{i}", color="red", fontsize=9, ha="left", va="top", weight='bold')

    ax.set_xlim(-0.5, N + 0.5)
    ax.set_ylim(M + 0.5, -0.5)  # Inverted y-axis for visual alignment
    ax.set_aspect('equal')
    # ax.legend()
    ax.set_title(f"Metro Lines for {base_name}")

def visualize_both(base_name):
    """
    Creates both visualizations side by side.
    """
    city_file = base_name + ".city"
    satoutput_file = base_name + ".satoutput"
    metromap_file = base_name + ".metromap"
    # metromap_file="temp.metromap"

    try:
        # Parse city file
        spec = parse_city(city_file)
        print(spec)
        # spec=MetroSpec(1,4,4,1,1,0,[(0,0)],[(3,3)],[])
        
        # Get SAT assignments and decode to grid
        assignments = get_assignments(satoutput_file)
        # assignments=[2,18,34,52,56,60]
        grid = decode_to_grid(spec, assignments)
        
        if(spec.scenario==2):
            for i,(px,py) in enumerate(spec.popular):
                grid[py][px]=f"P:{i+1} | "+grid[py][px] +" |"
        # print(grid)
        # Read metro paths
        metro_paths = read_metromap_file(metromap_file)

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot decoded grid on left
        plot_grid(ax1, grid)

        # Plot metro lines on right
        # if metro_paths is None or not assignments:
        #     ax2.text(0.5, 0.5, "Unsatisfiable problem\nor no metro paths found",
        #             ha='center', va='center', fontsize=12)
        #     ax2.set_xlim(0, 1)
        #     ax2.set_ylim(0, 1)
        #     ax2.axis('off')
        # else:
            # plot_metrolines(ax2, base_name, spec, metro_paths)
        plot_metrolines(ax2, base_name, spec, metro_paths)
        # plt.legend(loc="best")
        plt.tight_layout()
        
        # plt.tight_layout()
        output_img = f"{base_name}_metromap.png"
        plt.savefig(output_img)
        plt.show()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize.py <base_name>")
        sys.exit(1)
    else:
        base_name = sys.argv[1]
        if(base_name.find(".city")!=-1):
            base_name=base_name[:-5]
    
    visualize_both(base_name)