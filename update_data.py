#!/usr/bin/env python3
"""
Update visualization data files by MERGING new data from extracted_v5.
Preserves existing data and adds new entities/edges.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
EXTRACTED_V5 = BASE_DIR.parent / "extracted_v5"

# Vietnamese word mappings for medical terms (for ID to name conversion)
VIETNAMESE_MAPPINGS = {
    'TANG': 'tăng', 'GIAM': 'giảm', 'CAO': 'cao', 'THAP': 'thấp',
    'MAN': 'mạn', 'CAP': 'cấp', 'VIEM': 'viêm', 'BENH': 'bệnh',
    'DAU': 'đau', 'SOT': 'sốt', 'HO': 'ho', 'MET MOI': 'mệt mỏi',
    'BUON NON': 'buồn nôn', 'NON': 'nôn', 'TIEU CHAY': 'tiêu chảy',
    'TAO BON': 'táo bón', 'PHU': 'phù', 'XUAT HUYET': 'xuất huyết',
    'NHIEM TRUNG': 'nhiễm trùng', 'UNG THU': 'ung thư',
    'DONG': 'đông', 'MAU': 'máu', 'GAN': 'gan', 'THAN': 'thận',
    'PHOI': 'phổi', 'TIM': 'tim', 'MACH': 'mạch', 'DA': 'da',
    'XUONG': 'xương', 'KHOP': 'khớp', 'CO': 'cơ',
    'THAN KINH': 'thần kinh', 'NANG': 'nặng', 'NHE': 'nhẹ',
    'KHONG': 'không', 'VA': 'và', 'HOAC': 'hoặc',
    'AI TOAN': 'ái toan', 'BACH CAU': 'bạch cầu', 'HONG CAU': 'hồng cầu',
    'TIEU CAU': 'tiểu cầu', 'HUYET TUONG': 'huyết tương',
    'RUOU': 'rượu', 'MO': 'mỡ', 'THOAI HOA': 'thoái hóa',
    'DA DAY': 'dạ dày', 'RUOT': 'ruột', 'TRANG': 'trắng',
    'DO': 'đỏ', 'VANG': 'vàng', 'DEN': 'đen', 'XANH': 'xanh',
    'SAU': 'sau', 'TRUOC': 'trước', 'TREN': 'trên', 'DUOI': 'dưới',
    'TRONG': 'trong', 'NGOAI': 'ngoài', 'PHAI': 'phải', 'TRAI': 'trái',
    'KHO THO': 'khó thở', 'DICH': 'dịch', 'MANG': 'màng',
    'BUNG': 'bụng', 'NGUC': 'ngực', 'DAU': 'đầu', 'CO': 'cổ',
    'TAY': 'tay', 'CHAN': 'chân', 'LUNG': 'lưng', 'MAT': 'mắt',
    'MUI': 'mũi', 'HONG': 'họng', 'TAI': 'tai', 'MIENG': 'miệng',
    'LUOI': 'lưỡi', 'RANG': 'răng', 'LOI': 'lợi', 'HAU': 'hầu',
    'THANH QUAN': 'thanh quản', 'PHE QUAN': 'phế quản',
    'TUY': 'tụy', 'TUYENPHAI': 'tuyến phải', 'LAC': 'lách',
    'HOI CHUNG': 'hội chứng', 'TRIEU CHUNG': 'triệu chứng',
    'ROI LOAN': 'rối loạn', 'SUY': 'suy', 'TANG': 'tăng',
    'HUYET AP': 'huyết áp', 'NHIP TIM': 'nhịp tim',
    'PHAN': 'phân', 'NUOC TIEU': 'nước tiểu', 'DOM': 'đờm',
    'CHAN THUONG': 'chấn thương', 'NHIEM': 'nhiễm',
    'DI UNG': 'dị ứng', 'TU MIEN': 'tự miễn', 'DI TRUYEN': 'di truyền',
}


def id_to_name(entity_id):
    """Convert entity ID to Vietnamese name"""
    # Remove prefix (S_, M_, D_)
    name = entity_id
    if name.startswith(('S_', 'M_', 'D_')):
        name = name[2:]

    # Replace underscores with spaces
    name = name.replace('_', ' ')

    # Apply replacements (longer phrases first)
    for old, new in sorted(VIETNAMESE_MAPPINGS.items(), key=lambda x: -len(x[0])):
        name = re.sub(r'\b' + old + r'\b', new, name, flags=re.IGNORECASE)

    return name
ENTITIES_DIR = EXTRACTED_V5 / "entities"
ENTITIES_MANUAL_DIR = EXTRACTED_V5 / "entities_manual"
EDGES_DIR = EXTRACTED_V5 / "edges"


def load_existing_nodes(filepath):
    """Load existing nodes from visualization JSON file"""
    if not filepath.exists():
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert to dict by id for easy lookup
    return {node["id"]: node for node in data}


def load_existing_edges(filepath):
    """Load existing edges from visualization JSONL file.

    Normalizes context format to array for ASSOCIATED_WITH edges.
    """
    edges = []
    edge_set = set()

    if not filepath.exists():
        return edges, edge_set

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                edge = json.loads(line)

                # Normalize context to array format
                if edge.get("type") == "ASSOCIATED_WITH":
                    context = edge.get("context")
                    if context and isinstance(context, dict):
                        edge["context"] = [context]

                edges.append(edge)
                # Create key for deduplication (normalized for S-S edges)
                edge_key = (edge.get("from"), edge.get("to"), edge.get("type"))
                edge_set.add(edge_key)
            except json.JSONDecodeError:
                continue

    return edges, edge_set


def load_v5_entities(entity_type):
    """Load entities from extracted_v5/entities/{type}/ and entities_manual/"""
    entities = {}

    # Load from entities/{type}/*.json
    entity_dir = ENTITIES_DIR / entity_type
    if entity_dir.exists():
        for filepath in sorted(entity_dir.glob("*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entity_id = data.get("id", filepath.stem)
                    name = data.get("name", "")
                    entities[entity_id] = {"id": entity_id, "name": name}
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    else:
        print(f"Warning: {entity_dir} does not exist")

    # Load from entities_manual/ (both .json and .jsonl files)
    if ENTITIES_MANUAL_DIR.exists():
        type_lower = entity_type.lower()
        prefix = f"{entity_type}_"

        # Load .json files (JSON array format)
        for filepath in ENTITIES_MANUAL_DIR.glob(f"*{type_lower}*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            entity_id = item.get("id", "")
                            if entity_id.startswith(prefix):
                                name = item.get("name", "")
                                entities[entity_id] = {"id": entity_id, "name": name}
                    elif isinstance(data, dict):
                        entity_id = data.get("id", "")
                        if entity_id.startswith(prefix):
                            name = data.get("name", "")
                            entities[entity_id] = {"id": entity_id, "name": name}
            except Exception as e:
                print(f"Error reading manual {filepath}: {e}")

        # Load .jsonl files (JSONL format)
        for filepath in ENTITIES_MANUAL_DIR.glob(f"*{type_lower}*.jsonl"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        entity_id = data.get("id", "")
                        if entity_id.startswith(prefix):
                            name = data.get("name", "")
                            entities[entity_id] = {"id": entity_id, "name": name}
            except Exception as e:
                print(f"Error reading manual {filepath}: {e}")

    return entities


def load_v5_edges():
    """Load all edges from extracted_v5/edges/*.jsonl"""
    edges = []
    edge_set = set()

    if not EDGES_DIR.exists():
        print(f"Warning: {EDGES_DIR} does not exist")
        return edges, edge_set

    for filepath in sorted(EDGES_DIR.glob("*.jsonl")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)

                        # Extract source and target (handle both dict and string formats)
                        source = data.get("source")
                        target = data.get("target")

                        from_id = source.get("id") if isinstance(source, dict) else (source or data.get("from"))
                        to_id = target.get("id") if isinstance(target, dict) else (target or data.get("to"))
                        edge_type = data.get("edge_type") or data.get("type")

                        if not from_id or not to_id or not edge_type:
                            continue

                        # Deduplication key
                        edge_key = (from_id, to_id, edge_type)
                        if edge_key in edge_set:
                            continue
                        edge_set.add(edge_key)

                        # Build simplified edge
                        edge = {
                            "from": from_id,
                            "to": to_id,
                            "type": edge_type
                        }

                        # Add context for ASSOCIATED_WITH (support array format)
                        if edge_type == "ASSOCIATED_WITH":
                            # Try direct context first, then properties.context
                            context = data.get("context") or data.get("properties", {}).get("context")
                            if context:
                                # Handle both array and single object/string format
                                if isinstance(context, list):
                                    edge["context"] = context
                                elif isinstance(context, dict):
                                    edge["context"] = [context]
                                elif isinstance(context, str):
                                    edge["context"] = [context]

                        edges.append(edge)

                    except json.JSONDecodeError as e:
                        print(f"JSON error in {filepath.name}:{line_num}: {e}")

        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return edges, edge_set


def merge_nodes(existing_nodes, new_nodes, generate_missing=True):
    """Merge new nodes into existing, update names if empty.

    Args:
        existing_nodes: Dict of existing nodes by ID
        new_nodes: Dict of new nodes from v5 by ID
        generate_missing: If True, generate names from IDs for nodes without names
    """
    merged = existing_nodes.copy()
    added = 0
    updated_from_v5 = 0
    generated = 0

    # First, merge v5 entities
    for node_id, node in new_nodes.items():
        if node_id not in merged:
            merged[node_id] = node
            added += 1
        else:
            # Update name if existing is empty and new has name
            if not merged[node_id].get("name") and node.get("name"):
                merged[node_id]["name"] = node["name"]
                updated_from_v5 += 1

    # Then, generate names from IDs for remaining empty-name nodes
    if generate_missing:
        for node_id, node in merged.items():
            if not node.get("name"):
                generated_name = id_to_name(node_id)
                node["name"] = generated_name
                generated += 1

    return merged, added, updated_from_v5, generated


def normalize_edge_key(from_id, to_id, edge_type):
    """Create normalized edge key (direction-independent for S-S edges)"""
    # For ASSOCIATED_WITH between S-S, treat edges as undirected
    if edge_type == "ASSOCIATED_WITH":
        return (min(from_id, to_id), max(from_id, to_id), edge_type)
    return (from_id, to_id, edge_type)


def merge_contexts(existing_contexts, new_contexts):
    """Merge context arrays, removing duplicates"""
    all_contexts = []
    seen = set()

    for ctx in (existing_contexts or []) + (new_contexts or []):
        # Handle both string and dict contexts
        if isinstance(ctx, str):
            if ctx not in seen:
                seen.add(ctx)
                all_contexts.append(ctx)
        elif isinstance(ctx, dict):
            ctx_id = ctx.get("id") or str(ctx)
            if ctx_id not in seen:
                seen.add(ctx_id)
                all_contexts.append(ctx)

    return all_contexts


def merge_edges(existing_edges, existing_set, new_edges, new_set):
    """Merge new edges into existing with proper property merging.

    For ASSOCIATED_WITH edges: merge contexts from multiple sources.
    For other edges: merge properties without overwriting.
    """
    # Build lookup dict by normalized key
    edge_lookup = {}
    for i, edge in enumerate(existing_edges):
        key = normalize_edge_key(edge.get("from"), edge.get("to"), edge.get("type"))
        edge_lookup[key] = i

    merged = list(existing_edges)
    merged_set = set()
    for edge in existing_edges:
        key = normalize_edge_key(edge.get("from"), edge.get("to"), edge.get("type"))
        merged_set.add(key)

    added = 0
    context_merged = 0

    for edge in new_edges:
        edge_key = normalize_edge_key(edge.get("from"), edge.get("to"), edge.get("type"))
        edge_type = edge.get("type")

        if edge_key in merged_set:
            # Edge exists - merge properties
            existing_idx = edge_lookup.get(edge_key)
            if existing_idx is not None:
                existing_edge = merged[existing_idx]

                if edge_type == "ASSOCIATED_WITH":
                    # Merge contexts
                    existing_ctx = existing_edge.get("context", [])
                    new_ctx = edge.get("context", [])
                    merged_ctx = merge_contexts(existing_ctx, new_ctx)
                    if len(merged_ctx) > len(existing_ctx):
                        merged[existing_idx]["context"] = merged_ctx
                        context_merged += 1
                else:
                    # For other edge types, merge other properties if needed
                    for key, value in edge.items():
                        if key not in ("from", "to", "type") and key not in existing_edge:
                            existing_edge[key] = value
        else:
            # New edge - add it
            merged.append(edge)
            merged_set.add(edge_key)
            edge_lookup[edge_key] = len(merged) - 1
            added += 1

    print(f"   Contexts merged: {context_merged}")
    return merged, added


def save_nodes(nodes_dict, output_file):
    """Save nodes dict to JSON file"""
    nodes_list = sorted(nodes_dict.values(), key=lambda x: x["id"])

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(nodes_list, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(nodes_list)} nodes to {output_file.name}")


def deduplicate_edges(edges):
    """Deduplicate edges, treating ASSOCIATED_WITH as undirected.

    Merges contexts when duplicate ASSOCIATED_WITH edges are found.
    """
    edge_lookup = {}
    deduped = []

    for edge in edges:
        from_id = edge.get("from")
        to_id = edge.get("to")
        edge_type = edge.get("type")

        # For ASSOCIATED_WITH, use normalized key (alphabetical order)
        if edge_type == "ASSOCIATED_WITH":
            key = (min(from_id, to_id), max(from_id, to_id), edge_type)
        else:
            key = (from_id, to_id, edge_type)

        if key in edge_lookup:
            # Merge contexts for ASSOCIATED_WITH
            if edge_type == "ASSOCIATED_WITH":
                existing_idx = edge_lookup[key]
                existing_ctx = deduped[existing_idx].get("context", [])
                new_ctx = edge.get("context", [])

                # Merge contexts (handle both string and dict)
                seen = set()
                for c in existing_ctx:
                    if isinstance(c, str):
                        seen.add(c)
                    elif isinstance(c, dict):
                        seen.add(c.get("id") or str(c))

                for ctx in new_ctx:
                    if isinstance(ctx, str):
                        if ctx not in seen:
                            existing_ctx.append(ctx)
                            seen.add(ctx)
                    elif isinstance(ctx, dict):
                        ctx_id = ctx.get("id") or str(ctx)
                        if ctx_id not in seen:
                            existing_ctx.append(ctx)
                            seen.add(ctx_id)

                deduped[existing_idx]["context"] = existing_ctx
        else:
            # For ASSOCIATED_WITH, normalize direction (alphabetical order)
            if edge_type == "ASSOCIATED_WITH" and from_id > to_id:
                edge = edge.copy()
                edge["from"], edge["to"] = to_id, from_id

            edge_lookup[key] = len(deduped)
            deduped.append(edge)

    return deduped


def save_edges(edges, output_file):
    """Save edges to JSONL file after deduplication"""
    # Deduplicate before saving
    edges = deduplicate_edges(edges)
    edges = sorted(edges, key=lambda x: (x["from"], x["to"], x["type"]))

    with open(output_file, "w", encoding="utf-8") as f:
        for edge in edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    print(f"Saved {len(edges)} edges to {output_file.name}")


def main():
    print("=" * 60)
    print("Merging SMD Visualization Data from extracted_v5")
    print("=" * 60)

    # Load existing visualization data
    print("\n1. Loading existing visualization data...")
    existing_s = load_existing_nodes(BASE_DIR / "S_nodes.json")
    existing_m = load_existing_nodes(BASE_DIR / "M_nodes.json")
    existing_d = load_existing_nodes(BASE_DIR / "D_nodes.json")
    existing_edges, existing_edge_set = load_existing_edges(BASE_DIR / "all_edges.json")

    print(f"   Existing S: {len(existing_s)} nodes")
    print(f"   Existing M: {len(existing_m)} nodes")
    print(f"   Existing D: {len(existing_d)} nodes")
    print(f"   Existing edges: {len(existing_edges)}")

    # Load new data from v5
    print("\n2. Loading data from extracted_v5...")
    v5_s = load_v5_entities("S")
    v5_m = load_v5_entities("M")
    v5_d = load_v5_entities("D")
    v5_edges, v5_edge_set = load_v5_edges()

    print(f"   v5 S: {len(v5_s)} entities")
    print(f"   v5 M: {len(v5_m)} entities")
    print(f"   v5 D: {len(v5_d)} entities")
    print(f"   v5 edges: {len(v5_edges)}")

    # Merge nodes
    print("\n3. Merging nodes...")
    merged_s, s_added, s_updated, s_generated = merge_nodes(existing_s, v5_s)
    merged_m, m_added, m_updated, m_generated = merge_nodes(existing_m, v5_m)
    merged_d, d_added, d_updated, d_generated = merge_nodes(existing_d, v5_d)

    print(f"   S: +{s_added} new, {s_updated} from v5, {s_generated} generated → {len(merged_s)} total")
    print(f"   M: +{m_added} new, {m_updated} from v5, {m_generated} generated → {len(merged_m)} total")
    print(f"   D: +{d_added} new, {d_updated} from v5, {d_generated} generated → {len(merged_d)} total")

    # Merge edges
    print("\n4. Merging edges...")
    merged_edges, edges_added = merge_edges(existing_edges, existing_edge_set, v5_edges, v5_edge_set)
    print(f"   +{edges_added} new edges → {len(merged_edges)} total")

    # Count edge types
    edge_types = defaultdict(int)
    for e in merged_edges:
        edge_types[e["type"]] += 1
    print("\n   Edge types:")
    for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
        print(f"     {etype}: {count}")

    # Save files
    print("\n5. Saving merged files...")
    save_nodes(merged_s, BASE_DIR / "S_nodes.json")
    save_nodes(merged_m, BASE_DIR / "M_nodes.json")
    save_nodes(merged_d, BASE_DIR / "D_nodes.json")
    save_edges(merged_edges, BASE_DIR / "all_edges.json")

    print("\n" + "=" * 60)
    print("Done! Merged data from extracted_v5 into visualization files.")
    print("=" * 60)


if __name__ == "__main__":
    main()
