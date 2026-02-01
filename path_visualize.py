#!/usr/bin/env python3
"""
Find and visualize paths between two nodes in the knowledge graph.

Usage:
    python path_visualize.py --from <node_id> --to <node_id> [--paths 3] [--max-depth 6]

Examples:
    python path_visualize.py --from S_KHO_THO --to D_SUY_TIM
    python path_visualize.py -f S_HOI_HOP -t D_RUNG_NHI -p 5
    python path_visualize.py -f S_VANG_DA -t S_HOI_HOP -p 10 -d 4
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict, deque

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False
    print("Warning: pyvis not installed. Install with: pip install pyvis")

BASE_DIR = Path(__file__).parent

# =============================================================================
# DESIGN SYSTEM - Same as visualize_node.py
# =============================================================================

NODE_COLORS = {
    "S": "#3B82F6",  # Blue-500 - Symptom
    "M": "#F59E0B",  # Amber-500 - Mechanism
    "D": "#DC2626",  # Red-600 - Disease
}

EDGE_STYLES = {
    "S_D_SUGGESTS": {"color": "#6B7280", "dashes": False, "width": 2},
    "S_D_INDICATES": {"color": "#374151", "dashes": False, "width": 3},
    "S_D_RULES_OUT": {"color": "#991B1B", "dashes": [5, 5], "width": 2},
    "S_M_SUGGESTS": {"color": "#60A5FA", "dashes": False, "width": 2},
    "S_M_INDICATES": {"color": "#3B82F6", "dashes": False, "width": 3},
    "M_S_CAUSES": {"color": "#D97706", "dashes": False, "width": 3},
    "M_S_CONTRIBUTES_TO": {"color": "#F59E0B", "dashes": [5, 5], "width": 2},
    "M_M_CAUSES": {"color": "#B45309", "dashes": False, "width": 2},
    "M_M_LEADS_TO": {"color": "#92400E", "dashes": [8, 4], "width": 2},
    "M_M_CONTRIBUTES_TO": {"color": "#D97706", "dashes": [5, 5], "width": 2},
    "D_S_HAS_SYMPTOM": {"color": "#DC2626", "dashes": False, "width": 2},
    "D_M_HAS_MECHANISM": {"color": "#B91C1C", "dashes": False, "width": 2},
    "S_S_ASSOCIATED_WITH": {"color": "#9CA3AF", "dashes": [3, 3], "width": 1.5},
    "D_D_SUBTYPE_OF": {"color": "#A78BFA", "dashes": [4, 4], "width": 2},
}

DEFAULT_EDGE_STYLE = {"color": "#D1D5DB", "dashes": False, "width": 1.5}


def load_edges():
    """Load all edges from all_edges.json."""
    edges_file = BASE_DIR / "all_edges.json"
    edges = []
    with open(edges_file, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                edges.append(json.loads(line))
    return edges


def load_node_types_and_names():
    """Load node types and Vietnamese names from *_nodes.json files."""
    node_types = {}
    node_names = {}

    for prefix, filename in [("S", "S_nodes.json"), ("M", "M_nodes.json"), ("D", "D_nodes.json")]:
        filepath = BASE_DIR / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                for item in data:
                    if isinstance(item, str):
                        node_id = item
                        name = ""
                    else:
                        node_id = item.get("id", "")
                        name = item.get("name", "")

                    if node_id:
                        node_types[node_id] = prefix
                        if name:
                            node_names[node_id] = name

    return node_types, node_names


def build_adjacency_undirected(edges):
    """Build undirected adjacency list for BFS path finding."""
    adj = defaultdict(list)
    edge_lookup = {}  # (from, to) -> edge info

    for edge in edges:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        properties = edge.get("properties", {})
        context = edge.get("context")  # context is at top level

        # Store edge info for both directions (for lookup)
        edge_lookup[(from_id, to_id)] = edge
        reversed_edge = {"from": to_id, "to": from_id, "type": edge_type, "properties": properties, "reversed": True}
        if context:
            reversed_edge["context"] = context
        edge_lookup[(to_id, from_id)] = reversed_edge

        # Undirected adjacency for BFS
        adj[from_id].append(to_id)
        adj[to_id].append(from_id)

    return adj, edge_lookup


def get_context_ids(context):
    """Extract context IDs from context array."""
    if not context:
        return set()
    ids = set()
    ctx_list = context if isinstance(context, list) else [context]
    for ctx in ctx_list:
        if isinstance(ctx, dict):
            ctx_id = ctx.get("id")
            if ctx_id:
                ids.add(ctx_id)
        elif isinstance(ctx, str):
            ids.add(ctx)
    return ids


def validate_ss_contexts(path, edge_lookup):
    """
    Validate that all S-S edges in a path share at least one common context.

    Args:
        path: List of node IDs
        edge_lookup: Dict mapping (from, to) -> edge info

    Returns:
        (is_valid, common_contexts) where:
        - is_valid: True if all S-S edges share common context (or no S-S edges)
        - common_contexts: Set of shared context IDs (for display)
    """
    ss_contexts = []  # List of context sets for each S-S edge

    for i in range(len(path) - 1):
        n1, n2 = path[i], path[i + 1]

        # Check if both nodes are Symptoms
        if n1.startswith("S_") and n2.startswith("S_"):
            edge_info = edge_lookup.get((n1, n2)) or edge_lookup.get((n2, n1))
            if edge_info and edge_info.get("type") == "ASSOCIATED_WITH":
                context = edge_info.get("context")
                ctx_ids = get_context_ids(context)
                if ctx_ids:
                    ss_contexts.append(ctx_ids)
                else:
                    # S-S edge without context - invalid
                    return False, set()

    # No S-S edges = valid
    if not ss_contexts:
        return True, set()

    # Find intersection of all S-S contexts
    common = ss_contexts[0]
    for ctx_set in ss_contexts[1:]:
        common = common & ctx_set
        if not common:
            return False, set()

    return True, common


def find_all_paths_bfs(start, end, adj, edge_lookup, max_paths=3, max_depth=6):
    """
    Find multiple DIVERSE paths using BFS with S-S context validation.

    BFS explores level-by-level, ensuring paths through different first neighbors
    are discovered before going deeper.

    CONSTRAINT: All S-S (ASSOCIATED_WITH) edges in a path must share at least
    one common context (Disease or Mechanism). Different paths can use different contexts.

    Args:
        start: Starting node ID
        end: Ending node ID
        adj: Adjacency list (undirected)
        edge_lookup: Dict mapping (from, to) -> edge info
        max_paths: Maximum number of paths to return
        max_depth: Maximum path length (hops) to explore

    Returns:
        List of (path, common_context) tuples where:
        - path: List of node IDs
        - common_context: Set of shared context IDs for S-S edges (may be empty)
    """
    if start == end:
        return [([start], set())]

    found_paths = []
    seen_paths = set()  # Track unique paths (as tuples)
    first_hop_count = {}  # Count paths per first hop for diversity

    # Queue holds: (current_node, path_so_far, visited_set)
    queue = deque()
    queue.append((start, [start], {start}))

    while queue and len(found_paths) < max_paths * 3:  # Collect more, filter later
        current, path, visited = queue.popleft()
        current_depth = len(path) - 1

        if current_depth >= max_depth:
            continue

        # Get neighbors and sort for consistency
        neighbors = sorted(adj.get(current, []))

        for neighbor in neighbors:
            if neighbor in visited:
                continue

            new_path = path + [neighbor]
            new_visited = visited | {neighbor}

            if neighbor == end:
                # Found a path - check if unique
                path_tuple = tuple(new_path)
                if path_tuple in seen_paths:
                    continue
                seen_paths.add(path_tuple)

                # Validate S-S context constraint
                is_valid, common_ctx = validate_ss_contexts(new_path, edge_lookup)
                if not is_valid:
                    continue  # Skip paths with conflicting S-S contexts

                # Track first hop for diversity
                first_hop = new_path[1] if len(new_path) > 1 else None
                if first_hop:
                    first_hop_count[first_hop] = first_hop_count.get(first_hop, 0) + 1

                found_paths.append((new_path, common_ctx))
            else:
                # Continue exploring
                queue.append((neighbor, new_path, new_visited))

    # Sort by: (path_length, first_hop_frequency) to prioritize short & diverse paths
    def sort_key(item):
        p, _ = item
        first_hop = p[1] if len(p) > 1 else ""
        return (len(p), first_hop_count.get(first_hop, 0))

    found_paths.sort(key=sort_key)
    return found_paths[:max_paths]


def find_all_paths_dfs(start, end, adj, max_paths=3, max_depth=6):
    """
    Find multiple paths using DFS (legacy, kept for reference).
    Note: DFS tends to find similar paths. Use find_all_paths_bfs for diversity.
    """
    if start == end:
        return [[start]]

    found_paths = []

    def dfs(current, path, visited):
        if len(found_paths) >= max_paths * 3:
            return

        current_depth = len(path) - 1

        for neighbor in adj.get(current, []):
            if neighbor in visited:
                continue

            new_depth = current_depth + 1
            if new_depth > max_depth:
                continue

            new_path = path + [neighbor]

            if neighbor == end:
                found_paths.append(new_path)
            else:
                visited.add(neighbor)
                dfs(neighbor, new_path, visited)
                visited.remove(neighbor)

    dfs(start, [start], {start})
    found_paths.sort(key=len)
    return found_paths[:max_paths]


def get_edge_style(from_id, to_id, edge_type):
    """Get edge style based on node types and edge type."""
    from_type = from_id[0] if from_id else "?"
    to_type = to_id[0] if to_id else "?"

    style_key = f"{from_type}_{to_type}_{edge_type}"
    style = EDGE_STYLES.get(style_key, DEFAULT_EDGE_STYLE)

    # Arrow direction
    if (from_type == "D" and to_type == "S") or (from_type == "M" and to_type == "S"):
        arrows = "to"
    else:
        arrows = ""

    return {**style, "arrows": arrows}


def visualize_paths_pyvis(path_results, edge_lookup, node_types, node_names, start_id, end_id, output_file):
    """Create interactive visualization of paths using pyvis.

    Args:
        path_results: List of (path, common_context) tuples
    """
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#1F2937")
    net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=150)

    # Collect all nodes and edges from paths
    all_nodes = set()
    all_edges = []
    edge_set = set()

    for path, common_ctx in path_results:
        for node_id in path:
            all_nodes.add(node_id)

        # Get edges along the path
        for i in range(len(path) - 1):
            n1, n2 = path[i], path[i + 1]

            # Look up the actual edge
            edge_info = edge_lookup.get((n1, n2))
            if edge_info:
                # Use original direction
                if edge_info.get("reversed"):
                    from_id, to_id = edge_info["to"], edge_info["from"]
                else:
                    from_id, to_id = edge_info["from"], edge_info["to"]
                edge_type = edge_info["type"]
                properties = edge_info.get("properties", {})

                edge_key = (from_id, to_id, edge_type)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edge_data = {
                        "from": from_id,
                        "to": to_id,
                        "type": edge_type,
                        "properties": properties
                    }
                    # Include context if present (at top level)
                    if "context" in edge_info:
                        edge_data["context"] = edge_info["context"]
                    all_edges.append(edge_data)

    # Add nodes
    for node_id in all_nodes:
        node_type = node_types.get(node_id, "?")[0] if node_id in node_types else node_id[0]
        is_endpoint = node_id == start_id or node_id == end_id

        color = NODE_COLORS.get(node_type, "#9CA3AF")

        if is_endpoint:
            size = 35
            border_width = 4
        else:
            size = 22
            border_width = 2

        # Label
        label = node_names.get(node_id, node_id)

        # Tooltip
        name_vi = node_names.get(node_id, "")
        tooltip = f"<b>{node_id}</b>"
        if name_vi:
            tooltip += f"<br>{name_vi}"
        tooltip += f"<br>Type: {node_type}"
        if node_id == start_id:
            tooltip += "<br><b>[START]</b>"
        elif node_id == end_id:
            tooltip += "<br><b>[END]</b>"

        net.add_node(
            node_id,
            label=label,
            title=tooltip,
            color={
                "background": color,
                "border": color,
                "highlight": {
                    "background": color,
                    "border": "#1F2937"
                }
            },
            size=size,
            borderWidth=border_width,
            borderWidthSelected=5,
            font={"color": "#ffffff", "size": 12, "face": "arial"},
            shape="dot",
        )

    # Add edges
    for edge in all_edges:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        properties = edge.get("properties", {})

        style = get_edge_style(from_id, to_id, edge_type)

        # Build tooltip (plain text - pyvis doesn't render HTML in tooltips)
        from_name = node_names.get(from_id, from_id)
        to_name = node_names.get(to_id, to_id)

        tooltip_lines = [
            edge_type,
            f"{from_name} → {to_name}"
        ]

        # Add context info for ASSOCIATED_WITH edges (support array format)
        if edge_type == "ASSOCIATED_WITH":
            context = edge.get("context")
            if context:
                tooltip_lines.append("")
                tooltip_lines.append("Liên quan:")
                # Handle both array and single object format
                ctx_list = context if isinstance(context, list) else [context]
                for ctx in ctx_list:
                    ctx_name = ctx.get("name", "")
                    if ctx_name:
                        tooltip_lines.append(f"  • {ctx_name}")
            else:
                tooltip_lines.append("")
                tooltip_lines.append("⚠ Chưa có context")

        tooltip = "\n".join(tooltip_lines)

        net.add_edge(
            from_id,
            to_id,
            title=tooltip,
            color=style["color"],
            arrows=style["arrows"],
            width=style["width"],
            dashes=style["dashes"],
            smooth={"type": "continuous"},
        )

    net.save_graph(str(output_file))
    print(f"Saved: {output_file}")


def visualize_paths_text(path_results, edge_lookup, node_names, start_id, end_id):
    """Text-based visualization of paths.

    Args:
        path_results: List of (path, common_context) tuples
    """
    print(f"\n{'='*60}")
    print(f"Paths from {start_id} to {end_id}")
    print(f"{'='*60}")

    if not path_results:
        print("\nNo path found!")
        return

    first_path, _ = path_results[0]
    print(f"\nFound {len(path_results)} path(s), shortest = {len(first_path) - 1} hops\n")

    for i, (path, common_ctx) in enumerate(path_results, 1):
        print(f"Path {i} ({len(path) - 1} hops):")

        # Show common context for S-S edges if any
        if common_ctx:
            ctx_names = []
            for ctx_id in common_ctx:
                ctx_name = node_names.get(ctx_id, ctx_id)
                ctx_names.append(f"{ctx_name} ({ctx_id})")
            print(f"  [S-S context: {', '.join(ctx_names)}]")

        path_str = []
        for j, node_id in enumerate(path):
            node_name = node_names.get(node_id, node_id)
            if j < len(path) - 1:
                n1, n2 = path[j], path[j + 1]
                edge_info = edge_lookup.get((n1, n2))
                if edge_info:
                    edge_type = edge_info["type"]
                    path_str.append(f"  {node_name} ({node_id})")
                    path_str.append(f"    --[{edge_type}]-->")
            else:
                path_str.append(f"  {node_name} ({node_id})")

        print("\n".join(path_str))
        print()


def main():
    parser = argparse.ArgumentParser(description="Find and visualize paths between two nodes")
    parser.add_argument("--from", "-f", dest="from_node", required=True, help="Start node ID")
    parser.add_argument("--to", "-t", dest="to_node", required=True, help="End node ID")
    parser.add_argument("--paths", "-p", type=int, default=3, choices=range(1, 21), metavar="1-20",
                        help="Max number of paths to find (default: 3, max: 20)")
    parser.add_argument("--max-depth", "-d", type=int, default=6, choices=range(1, 11), metavar="1-10",
                        help="Max path length in hops (default: 6, max: 10)")
    parser.add_argument("--text", action="store_true", help="Text output only (no HTML)")
    parser.add_argument("--output", "-o", type=str, help="Output HTML filename")
    args = parser.parse_args()

    # Load data
    print("Loading edges...")
    edges = load_edges()
    print(f"Loaded {len(edges)} edges")

    print("Loading node types and names...")
    node_types, node_names = load_node_types_and_names()
    print(f"Loaded {len(node_types)} nodes")

    # Build adjacency
    adj, edge_lookup = build_adjacency_undirected(edges)

    # Validate nodes
    if args.from_node not in adj:
        print(f"Error: Start node '{args.from_node}' not found or has no edges.")
        return
    if args.to_node not in adj:
        print(f"Error: End node '{args.to_node}' not found or has no edges.")
        return

    # Find paths using BFS for diversity (with S-S context validation)
    print(f"\nFinding paths from {args.from_node} to {args.to_node} (max {args.paths}, depth {args.max_depth})...")
    path_results = find_all_paths_bfs(args.from_node, args.to_node, adj, edge_lookup, args.paths, args.max_depth)

    if not path_results:
        print("No path found between the two nodes.")
        print("Note: Paths with S-S edges require all S-S edges to share common context (Disease/Mechanism).")
        return

    lengths = [len(p) - 1 for p, _ in path_results]
    print(f"Found {len(path_results)} path(s), lengths: {min(lengths)}-{max(lengths)} hops")

    # Visualize
    if args.text or not HAS_PYVIS:
        visualize_paths_text(path_results, edge_lookup, node_names, args.from_node, args.to_node)
    else:
        output_file = args.output or f"path_{args.from_node}_to_{args.to_node}.html"
        output_path = BASE_DIR / output_file
        visualize_paths_pyvis(path_results, edge_lookup, node_types, node_names,
                              args.from_node, args.to_node, output_path)
        print(f"\nOpen in browser: {output_path}")

    # Print paths summary
    print("\n--- Paths Summary ---")
    for i, (path, common_ctx) in enumerate(path_results, 1):
        path_str = " -> ".join(path)
        if common_ctx:
            ctx_list = ", ".join(common_ctx)
            print(f"Path {i}: {path_str}  [context: {ctx_list}]")
        else:
            print(f"Path {i}: {path_str}")


if __name__ == "__main__":
    main()
