#!/usr/bin/env python3
"""
Visualize graph centered on a node with configurable depth levels.

Usage:
    python visualize_node.py --entity <node_id> [--level 1|2|3] [--edges 20]

Examples:
    python visualize_node.py --entity S_KHO_THO
    python visualize_node.py --entity D_SUY_TIM --level 2
    python visualize_node.py -e M_GIAM_CUNG_LUONG_TIM -l 3 -E 25
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False
    print("Warning: pyvis not installed. Install with: pip install pyvis")

BASE_DIR = Path(__file__).parent

# =============================================================================
# DESIGN SYSTEM - Medical Knowledge Graph Visualization
# =============================================================================

# Node colors - Fixed by entity type (không đổi theo ngữ cảnh)
NODE_COLORS = {
    "S": "#3B82F6",  # Blue-500 - Symptom (thông tin đầu vào, trung tính)
    "M": "#F59E0B",  # Amber-500 - Mechanism (giải thích, causal reasoning)
    "D": "#DC2626",  # Red-600 - Disease (chẩn đoán, quyết định)
}

NODE_COLORS_LIGHT = {
    "S": "#DBEAFE",  # Blue background
    "M": "#FEF3C7",  # Amber background
    "D": "#FEE2E2",  # Red background
}

# Edge styles based on relationship type and node pair
# Format: (from_type, to_type, edge_type) -> style dict
EDGE_STYLES = {
    # S → D: Inference edges
    "S_D_SUGGESTS": {"color": "#6B7280", "dashes": False, "width": 2},      # gray-500, solid (typical)
    "S_D_INDICATES": {"color": "#374151", "dashes": False, "width": 3},     # gray-700, solid, thicker (strong)
    "S_D_RULES_OUT": {"color": "#991B1B", "dashes": [5, 5], "width": 2},    # red-800, dashed

    # S → M: Inference
    "S_M_SUGGESTS": {"color": "#60A5FA", "dashes": False, "width": 2},      # blue→amber gradient approx
    "S_M_INDICATES": {"color": "#3B82F6", "dashes": False, "width": 3},

    # M → S: Causal (mechanism causes symptom)
    "M_S_CAUSES": {"color": "#D97706", "dashes": False, "width": 3},        # amber-600, solid
    "M_S_CONTRIBUTES_TO": {"color": "#F59E0B", "dashes": [5, 5], "width": 2},  # amber-500, dashed

    # M → M: Causal chain
    "M_M_CAUSES": {"color": "#B45309", "dashes": False, "width": 2},        # amber-700
    "M_M_LEADS_TO": {"color": "#92400E", "dashes": [8, 4], "width": 2},     # amber-800, dashed
    "M_M_CONTRIBUTES_TO": {"color": "#D97706", "dashes": [5, 5], "width": 2},

    # D → S: Disease has symptom
    "D_S_HAS_SYMPTOM": {"color": "#DC2626", "dashes": False, "width": 2},   # red-600

    # D → M: Disease has mechanism
    "D_M_HAS_MECHANISM": {"color": "#B91C1C", "dashes": False, "width": 2}, # red-700

    # S ↔ S: Association
    "S_S_ASSOCIATED_WITH": {"color": "#9CA3AF", "dashes": [3, 3], "width": 1.5},  # gray-400, dotted

    # D ↔ D: Differential (if any)
    "D_D_SUBTYPE_OF": {"color": "#A78BFA", "dashes": [4, 4], "width": 2},   # violet-400, dotted
}

# Default edge style
DEFAULT_EDGE_STYLE = {"color": "#D1D5DB", "dashes": False, "width": 1.5}  # gray-300


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
                    # Support both old format (array of strings) and new format (array of {id, name})
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


def build_adjacency(edges):
    """Build adjacency list from edges."""
    adj = defaultdict(list)
    for edge in edges:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        properties = edge.get("properties", {})
        adj[from_id].append({"to": to_id, "type": edge_type, "dir": "out", "properties": properties})
        adj[to_id].append({"from": from_id, "type": edge_type, "dir": "in", "properties": properties})
    return adj


def get_neighbors(node_id, adj, max_edges=15):
    """Get neighbors of a node, limited to max_edges."""
    neighbors = adj.get(node_id, [])
    # Prioritize diverse edge types
    by_type = defaultdict(list)
    for n in neighbors:
        by_type[n["type"]].append(n)

    selected = []
    # Round-robin selection to get variety
    while len(selected) < max_edges and by_type:
        for etype in list(by_type.keys()):
            if by_type[etype]:
                selected.append(by_type[etype].pop(0))
                if not by_type[etype]:
                    del by_type[etype]
            if len(selected) >= max_edges:
                break
    return selected


def find_internal_edges(nodes, all_edges, edge_set):
    """Find edges between nodes already in the graph (e.g., M->S CAUSES)."""
    internal_edges = []
    node_set = set(nodes)

    for edge in all_edges:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        properties = edge.get("properties", {})

        # Both nodes must be in our graph
        if from_id in node_set and to_id in node_set:
            edge_key = (from_id, to_id, edge_type)
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                internal_edges.append({
                    "from": from_id,
                    "to": to_id,
                    "type": edge_type,
                    "properties": properties
                })

    return internal_edges


def expand_graph(center_id, adj, all_edges, level=1, max_edges=7, cross=False):
    """
    Expand graph from center node to given level.

    max_edges: số edges tối đa cho MỖI node ở MỖI level
    - Level 1: center có tối đa max_edges neighbors
    - Level 2: mỗi node từ level 1 có thêm max_edges neighbors mới
    - ...
    """
    nodes = {center_id}
    edges = []
    edge_set = set()
    node_levels = {center_id: 0}  # Track which level each node was added

    current_level_nodes = {center_id}

    for lvl in range(1, level + 1):
        next_level_nodes = set()

        for node_id in current_level_nodes:
            # Get neighbors, but only count NEW nodes toward max_edges limit
            all_neighbors = adj.get(node_id, [])

            # Prioritize diverse edge types
            by_type = defaultdict(list)
            for n in all_neighbors:
                by_type[n["type"]].append(n)

            new_neighbors_count = 0
            selected = []

            # Round-robin selection to get variety, but only count new nodes
            while new_neighbors_count < max_edges and by_type:
                for etype in list(by_type.keys()):
                    if by_type[etype]:
                        n = by_type[etype].pop(0)
                        if not by_type[etype]:
                            del by_type[etype]

                        # Determine neighbor id
                        if n["dir"] == "out":
                            neighbor_id = n["to"]
                        else:
                            neighbor_id = n["from"]

                        # Check if this is a new node
                        is_new_node = neighbor_id not in nodes

                        # Add edge
                        if n["dir"] == "out":
                            from_id, to_id = node_id, n["to"]
                        else:
                            from_id, to_id = n["from"], node_id

                        edge_key = (from_id, to_id, n["type"])
                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append({
                                "from": from_id,
                                "to": to_id,
                                "type": n["type"],
                                "properties": n.get("properties", {})
                            })

                            if is_new_node:
                                nodes.add(neighbor_id)
                                node_levels[neighbor_id] = lvl
                                next_level_nodes.add(neighbor_id)
                                new_neighbors_count += 1

                        if new_neighbors_count >= max_edges:
                            break

        current_level_nodes = next_level_nodes  # Only expand from NEW nodes

    # Find all internal edges between nodes if cross=True
    if cross:
        internal = find_internal_edges(nodes, all_edges, edge_set)
        edges.extend(internal)

    return nodes, edges


def get_edge_style(from_id, to_id, edge_type):
    """Get edge style based on node types and edge type."""
    from_type = from_id[0] if from_id else "?"
    to_type = to_id[0] if to_id else "?"

    # Build style key
    style_key = f"{from_type}_{to_type}_{edge_type}"
    style = EDGE_STYLES.get(style_key, DEFAULT_EDGE_STYLE)

    # Determine arrow direction
    # D→S, M→S: directed (arrows)
    # D↔M, M↔M, S↔S: undirected (no arrows)
    if (from_type == "D" and to_type == "S") or (from_type == "M" and to_type == "S"):
        arrows = "to"
    else:
        arrows = ""

    return {**style, "arrows": arrows}


def visualize_pyvis(center_id, nodes, edges, node_types, node_names, output_file):
    """Create interactive visualization using pyvis."""
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#1F2937")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=200)

    # Add nodes with medical design system
    for node_id in nodes:
        node_type = node_types.get(node_id, "?")[0] if node_id in node_types else node_id[0]
        is_center = node_id == center_id

        # Colors
        color = NODE_COLORS.get(node_type, "#9CA3AF")
        border_color = color  # Same as fill for consistency

        # Size and border based on focus
        if is_center:
            size = 35
            border_width = 4
        else:
            size = 22
            border_width = 2

        # Label: prefer Vietnamese name, fallback to ID
        if node_id in node_names:
            label = node_names[node_id]
        else:
            label = node_id  # Keep original ID, don't modify

        # Tooltip with full info (plain text)
        name_vi = node_names.get(node_id, "")
        tooltip_lines = [node_id]
        if name_vi:
            tooltip_lines.append(name_vi)
        tooltip_lines.append(f"Loại: {node_type}")
        tooltip = "\n".join(tooltip_lines)

        net.add_node(
            node_id,
            label=label,
            title=tooltip,
            color={
                "background": color,
                "border": border_color,
                "highlight": {
                    "background": color,
                    "border": "#1F2937"  # Dark border on highlight
                }
            },
            size=size,
            borderWidth=border_width,
            borderWidthSelected=5,
            font={"color": "#ffffff", "size": 12, "face": "arial"},
            shape="dot",
        )

    # Add edges with style based on relationship
    for edge in edges:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        properties = edge.get("properties", {})

        style = get_edge_style(from_id, to_id, edge_type)

        # Build tooltip for edge (plain text)
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

    # Save
    net.save_graph(str(output_file))
    print(f"Saved: {output_file}")


def visualize_text(center_id, nodes, edges, node_types):
    """Simple text-based visualization."""
    print(f"\n{'='*60}")
    print(f"Center: {center_id}")
    print(f"{'='*60}")
    print(f"\nNodes ({len(nodes)}):")
    for node_id in sorted(nodes):
        marker = " *" if node_id == center_id else ""
        ntype = node_types.get(node_id, "?")
        print(f"  [{ntype}] {node_id}{marker}")

    print(f"\nEdges ({len(edges)}):")
    for edge in edges:
        print(f"  {edge['from']} --[{edge['type']}]--> {edge['to']}")


def main():
    parser = argparse.ArgumentParser(description="Visualize graph centered on a node")
    parser.add_argument("--entity", "-e", required=True, help="Center node ID (e.g., S_KHO_THO, D_SUY_TIM)")
    parser.add_argument("--level", "-l", type=int, default=1, choices=[1, 2, 3], help="Expansion level (default: 1, max: 3)")
    parser.add_argument("--edges", "--max-edges", "-E", type=int, default=7, choices=range(1, 11), metavar="1-10", help="Max edges per node per level (default: 7, max: 10)")
    parser.add_argument("--cross", "-c", choices=["yes", "no"], default="no", help="Find all edges between nodes (default: no)")
    parser.add_argument("--text", "-t", action="store_true", help="Text output only (no HTML)")
    parser.add_argument("--output", "-o", type=str, help="Output HTML filename")
    args = parser.parse_args()

    # Alias for backward compatibility
    args.node_id = args.entity

    # Load data
    print("Loading edges...")
    edges = load_edges()
    print(f"Loaded {len(edges)} edges")

    print("Loading node types and names...")
    node_types, node_names = load_node_types_and_names()
    print(f"Loaded {len(node_types)} nodes, {len(node_names)} with Vietnamese names")

    # Validate node exists
    if args.node_id not in node_types:
        print(f"Warning: Node '{args.node_id}' not found in node list. Proceeding anyway...")

    # Build adjacency
    adj = build_adjacency(edges)

    # Check if node has any edges
    if args.node_id not in adj:
        print(f"Error: Node '{args.node_id}' has no edges in the graph.")
        return

    # Expand graph
    cross = args.cross == "yes"
    print(f"\nExpanding from {args.node_id} (level={args.level}, edges={args.edges}, cross={cross})...")
    nodes, graph_edges = expand_graph(args.node_id, adj, edges, args.level, args.edges, cross)
    print(f"Result: {len(nodes)} nodes, {len(graph_edges)} edges")

    # Visualize
    if args.text or not HAS_PYVIS:
        visualize_text(args.node_id, nodes, graph_edges, node_types)
    else:
        output_file = args.output or f"{args.node_id}_graph.html"
        output_path = BASE_DIR / output_file
        visualize_pyvis(args.node_id, nodes, graph_edges, node_types, node_names, output_path)
        print(f"\nOpen in browser: {output_path}")

    # Legend
    print("\n--- Legend ---")
    print("Nodes:")
    print("  🔵 S (Symptom)  = Xanh dương #3B82F6 - Thông tin đầu vào")
    print("  🟠 M (Mechanism) = Cam #F59E0B - Cơ chế sinh lý bệnh")
    print("  🔴 D (Disease)   = Đỏ #DC2626 - Chẩn đoán")
    print("Edges:")
    print("  D→S, M→S: có mũi tên (directed)")
    print("  D↔M, M↔M, S↔S: không mũi tên (undirected)")
    print("  Solid = primary, Dashed = secondary/weak")
    print("Center node: larger + thicker border")


if __name__ == "__main__":
    main()
