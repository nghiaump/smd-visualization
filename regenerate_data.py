#!/usr/bin/env python3
"""
Regenerate visualization data files FROM SCRATCH using extracted_v5.
Replaces existing data with fresh data from the source.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
EXTRACTED_V5 = BASE_DIR.parent / "extracted_v5"
ENTITIES_DIR = EXTRACTED_V5 / "entities"
ENTITIES_MANUAL_DIR = EXTRACTED_V5 / "entities_manual"
EDGES_DIR = EXTRACTED_V5 / "edges"

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
    'TUY': 'tụy', 'LAC': 'lách',
    'HOI CHUNG': 'hội chứng', 'TRIEU CHUNG': 'triệu chứng',
    'ROI LOAN': 'rối loạn', 'SUY': 'suy',
    'HUYET AP': 'huyết áp', 'NHIP TIM': 'nhịp tim',
    'PHAN': 'phân', 'NUOC TIEU': 'nước tiểu', 'DOM': 'đờm',
    'CHAN THUONG': 'chấn thương', 'NHIEM': 'nhiễm',
    'DI UNG': 'dị ứng', 'TU MIEN': 'tự miễn', 'DI TRUYEN': 'di truyền',
    'NHOI': 'nhồi', 'XO': 'xơ', 'THAC': 'thác', 'HUYEN': 'huyền',
    'AC TINH': 'ác tính', 'LANH TINH': 'lành tính',
    'TRANG': 'trạng', 'THAI': 'thái', 'KY': 'kỳ', 'GIAI DOAN': 'giai đoạn',
}


def id_to_name(entity_id: str) -> str:
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


def load_entities(entity_type: str) -> dict:
    """Load all entities of a type from extracted_v5"""
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

    # Generate names from IDs for entities without names
    for entity_id, node in entities.items():
        if not node.get("name"):
            node["name"] = id_to_name(entity_id)

    return entities


def load_all_edges() -> list:
    """Load all edges from extracted_v5/edges/*.jsonl"""
    edges = []
    edge_set = set()

    if not EDGES_DIR.exists():
        print(f"Warning: {EDGES_DIR} does not exist")
        return edges

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

                        # Normalize for ASSOCIATED_WITH (undirected)
                        if edge_type == "ASSOCIATED_WITH":
                            edge_key = (min(from_id, to_id), max(from_id, to_id), edge_type)
                            if edge_key in edge_set:
                                # Merge contexts
                                existing_idx = None
                                for i, e in enumerate(edges):
                                    if (min(e["from"], e["to"]), max(e["from"], e["to"]), e["type"]) == edge_key:
                                        existing_idx = i
                                        break
                                if existing_idx is not None:
                                    new_ctx = data.get("context") or data.get("properties", {}).get("context") or []
                                    if isinstance(new_ctx, dict):
                                        new_ctx = [new_ctx]
                                    existing_ctx = edges[existing_idx].get("context", [])
                                    # Merge without duplicates
                                    seen_ids = {c.get("id") if isinstance(c, dict) else c for c in existing_ctx}
                                    for ctx in new_ctx:
                                        ctx_id = ctx.get("id") if isinstance(ctx, dict) else ctx
                                        if ctx_id not in seen_ids:
                                            existing_ctx.append(ctx)
                                            seen_ids.add(ctx_id)
                                    edges[existing_idx]["context"] = existing_ctx
                                continue
                            edge_set.add(edge_key)
                            # Normalize direction
                            if from_id > to_id:
                                from_id, to_id = to_id, from_id
                        else:
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

                        # Add context for ASSOCIATED_WITH
                        if edge_type == "ASSOCIATED_WITH":
                            context = data.get("context") or data.get("properties", {}).get("context")
                            if context:
                                if isinstance(context, list):
                                    edge["context"] = context
                                elif isinstance(context, dict):
                                    edge["context"] = [context]
                                elif isinstance(context, str):
                                    edge["context"] = [context]

                        # Add properties for visualization (optional, for tooltips)
                        props = data.get("properties", {})
                        if props.get("explanation"):
                            edge["properties"] = {"explanation": props["explanation"]}

                        edges.append(edge)

                    except json.JSONDecodeError as e:
                        print(f"JSON error in {filepath.name}:{line_num}: {e}")

        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return edges


def collect_referenced_entities(edges: list) -> dict:
    """Collect all entity IDs referenced in edges"""
    referenced = {"S": set(), "M": set(), "D": set()}

    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")

        for entity_id in [from_id, to_id]:
            if entity_id.startswith("S_"):
                referenced["S"].add(entity_id)
            elif entity_id.startswith("M_"):
                referenced["M"].add(entity_id)
            elif entity_id.startswith("D_"):
                referenced["D"].add(entity_id)

        # Also collect from context
        for ctx in edge.get("context", []):
            if isinstance(ctx, dict):
                ctx_id = ctx.get("id", "")
            else:
                ctx_id = ctx
            if ctx_id.startswith("S_"):
                referenced["S"].add(ctx_id)
            elif ctx_id.startswith("M_"):
                referenced["M"].add(ctx_id)
            elif ctx_id.startswith("D_"):
                referenced["D"].add(ctx_id)

    return referenced


def save_nodes(entities: dict, output_file: Path):
    """Save entities to JSON array file"""
    nodes_list = sorted(entities.values(), key=lambda x: x["id"])

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(nodes_list, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(nodes_list)} nodes to {output_file.name}")


def save_edges(edges: list, output_file: Path):
    """Save edges to JSONL file"""
    edges = sorted(edges, key=lambda x: (x["from"], x["to"], x["type"]))

    with open(output_file, "w", encoding="utf-8") as f:
        for edge in edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    print(f"Saved {len(edges)} edges to {output_file.name}")


def main():
    print("=" * 60)
    print("REGENERATING SMD Visualization Data FROM SCRATCH")
    print("Source: extracted_v5/")
    print("=" * 60)

    # Load all entities
    print("\n1. Loading entities from extracted_v5...")
    entities_s = load_entities("S")
    entities_m = load_entities("M")
    entities_d = load_entities("D")

    print(f"   S: {len(entities_s)} entities")
    print(f"   M: {len(entities_m)} entities")
    print(f"   D: {len(entities_d)} entities")

    # Load all edges
    print("\n2. Loading edges from extracted_v5/edges/...")
    edges = load_all_edges()
    print(f"   Total edges: {len(edges)}")

    # Collect referenced entities from edges
    print("\n3. Checking for entities referenced in edges but not in entity files...")
    referenced = collect_referenced_entities(edges)

    # Add missing entities (generate names from IDs)
    missing_s = referenced["S"] - set(entities_s.keys())
    missing_m = referenced["M"] - set(entities_m.keys())
    missing_d = referenced["D"] - set(entities_d.keys())

    for entity_id in missing_s:
        entities_s[entity_id] = {"id": entity_id, "name": id_to_name(entity_id)}
    for entity_id in missing_m:
        entities_m[entity_id] = {"id": entity_id, "name": id_to_name(entity_id)}
    for entity_id in missing_d:
        entities_d[entity_id] = {"id": entity_id, "name": id_to_name(entity_id)}

    print(f"   Added {len(missing_s)} missing S entities from edges")
    print(f"   Added {len(missing_m)} missing M entities from edges")
    print(f"   Added {len(missing_d)} missing D entities from edges")

    # Count edge types
    edge_types = defaultdict(int)
    for e in edges:
        edge_types[e["type"]] += 1
    print("\n4. Edge type distribution:")
    for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
        print(f"   {etype}: {count}")

    # Save files
    print("\n5. Saving visualization files...")
    save_nodes(entities_s, BASE_DIR / "S_nodes.json")
    save_nodes(entities_m, BASE_DIR / "M_nodes.json")
    save_nodes(entities_d, BASE_DIR / "D_nodes.json")
    save_edges(edges, BASE_DIR / "all_edges.json")

    # Summary
    total_nodes = len(entities_s) + len(entities_m) + len(entities_d)
    print("\n" + "=" * 60)
    print("REGENERATION COMPLETE")
    print(f"Total nodes: {total_nodes} (S:{len(entities_s)}, M:{len(entities_m)}, D:{len(entities_d)})")
    print(f"Total edges: {len(edges)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
