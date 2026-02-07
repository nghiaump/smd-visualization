# SMD Knowledge Graph Visualization

> **Version**: 1.7.0
> **Scripts**: `visualize_node.py`, `path_visualize.py`
> **Output**: Interactive HTML (pyvis)

---

## Quick Start

```bash
cd smd_visualization

# Cài đặt dependency
pip install pyvis

# Visualize node
python visualize_node.py --entity D_SUY_TIM --level 2
```

---

## Cú pháp

```bash
python visualize_node.py --entity <node_id> [OPTIONS]
```

### Parameters

| Đầy đủ | Rút gọn | Default | Mô tả |
|--------|---------|---------|-------|
| `--entity` | `-e` | *(bắt buộc)* | Node ID trung tâm (VD: `S_KHO_THO`, `D_SUY_TIM`) |
| `--level` | `-l` | `1` | Độ sâu mở rộng: 1, 2, hoặc 3 |
| `--edges` | `-E` | `7` | Số edges tối đa mỗi node mỗi level (1-10) |
| `--cross` | `-c` | `no` | Tìm tất cả edges giữa các nodes: `yes` hoặc `no` |
| `--text` | `-t` | - | Output text thay vì HTML |
| `--output` | `-o` | `{entity}_graph.html` | Tên file HTML output |

### Ý nghĩa của --edges (-E)

`-E` là số nodes MỚI tối đa mà mỗi node có thể kết nối ở mỗi level:

```
Level 1: center → tối đa E nodes mới
Level 2: mỗi node level 1 → tối đa E nodes mới
Level 3: mỗi node level 2 → tối đa E nodes mới
...
```

Ví dụ với `-e S_HOI_HOP -l 2 -E 7`:
- Level 1: S_HOI_HOP kết nối 7 nodes
- Level 2: mỗi trong 7 nodes đó kết nối thêm tối đa 7 nodes mới
- Kết quả: ~27 nodes (1 + 7 + ~19)

### Ví dụ

```bash
# Dạng đầy đủ
python visualize_node.py --entity S_KHO_THO --level 2 --edges 10 --cross yes
python visualize_node.py --entity D_SUY_TIM --level 3 --output suy_tim.html
python visualize_node.py --entity M_ROI_LOAN_NHIP --text

# Dạng rút gọn
python visualize_node.py -e S_KHO_THO -l 2 -E 10 -c yes
python visualize_node.py -e D_SUY_TIM -l 3 -o suy_tim.html
python visualize_node.py -e M_ROI_LOAN_NHIP -t

# Level 1 - chỉ neighbors trực tiếp (default)
python visualize_node.py -e S_KHO_THO

# Level 3 với cross edges
python visualize_node.py -e D_RUNG_NHI -l 3 -E 10 -c yes
```

### So sánh --cross

| `--cross` | Mô tả | Kết quả |
|-----------|-------|---------|
| `no` (default) | Chỉ lấy edges từ expansion | Ít edges, graph đơn giản |
| `yes` | Tìm tất cả edges giữa các nodes | Nhiều edges, graph đầy đủ hơn |

Ví dụ với `S_HOI_HOP -l 2 -E 7`:
- `--cross no`: 27 nodes, ~50 edges
- `--cross yes`: 27 nodes, 104 edges

---

## Path Visualization

Tìm và visualize **đa dạng đường đi** giữa 2 nodes sử dụng BFS với **S-S context validation**.

### Cú pháp

```bash
python path_visualize.py --from <node_id> --to <node_id> [OPTIONS]
```

### Parameters

| Đầy đủ | Rút gọn | Default | Mô tả |
|--------|---------|---------|-------|
| `--from` | `-f` | *(bắt buộc)* | Node ID bắt đầu |
| `--to` | `-t` | *(bắt buộc)* | Node ID kết thúc |
| `--paths` | `-p` | `3` | Số paths tối đa trả về (1-20) |
| `--max-depth` | `-d` | `6` | Độ sâu tối đa (hops) để tìm kiếm (1-10) |
| `--text` | - | - | Output text thay vì HTML |
| `--output` | `-o` | `path_{from}_to_{to}.html` | Tên file HTML output |

### Thuật toán

- **BFS (Breadth-First Search)** - tìm paths level-by-level
- Ưu tiên **paths ngắn và đa dạng** (qua các first-hop khác nhau)
- Tránh cycles (mỗi node chỉ xuất hiện 1 lần trong path)
- Kết quả được **sắp xếp theo độ dài và đa dạng**
- Trả về top `-p` paths

### S-S Context Validation

Khi path chứa edges **S-S (ASSOCIATED_WITH)**, tất cả S-S edges trong path đó **phải có chung ít nhất 1 context** (Disease hoặc Mechanism).

**Lý do**: Hai symptoms "đi cùng nhau" phải có lý do lâm sàng chung. Ví dụ:
- `S_KHO_THO` ↔ `S_HOI_HOP` liên quan qua **Suy tim**, **Cường giáp**, **Thiếu máu**
- Nếu path có 2 S-S edges, cả 2 phải có chung ít nhất 1 bệnh/cơ chế

**Ví dụ path hợp lệ**:
```
S_DAU_BUNG → D_BENH_CROHN → S_SOT → S_DAU_CO
                              ↑
                    S-S edge có context: D_SOT_DENGUE, M_SAN_SINH_CYTOKINE
```

**Ví dụ path KHÔNG hợp lệ** (bị loại bỏ):
```
S_A → S_B → S_C
  ↑     ↑
  context: D_X    context: D_Y (khác nhau → invalid)
```

### Ví dụ

```bash
# Tìm 3 paths (default), max 6 hops (default)
python path_visualize.py -f S_KHO_THO -t D_SUY_TIM

# Tìm 10 paths, giới hạn 4 hops
python path_visualize.py -f S_MET_MOI -t S_HOI_HOP -p 10 -d 4

# Tìm 5 paths với depth lớn hơn
python path_visualize.py -f S_VANG_DA -t S_HOI_HOP -p 5 -d 6

# Output text (hiển thị context)
python path_visualize.py -f S_DAU_BUNG -t S_DAU_CO -p 5 --text
```

### Output

```
Finding paths from S_DAU_BUNG to S_DAU_CO (max 5, depth 6)...
Found 5 path(s), lengths: 2-3 hops

Path 1 (2 hops):
  Đau bụng (S_DAU_BUNG)
    --[CAUSES]-->
  Rối loạn chức năng tế bào gan (M_ROI_LOAN_CHUC_NANG_TE_BAO_GAN)
    --[CONTRIBUTES_TO]-->
  Đau cơ (S_DAU_CO)

Path 2 (3 hops):
  [S-S context: D_NHIEM_VIRUS, D_VIEM_CO]
  Đau bụng (S_DAU_BUNG)
    --[HAS_SYMPTOM]-->
  Bệnh Addison (D_BENH_ADDISON)
    --[SUGGESTS]-->
  Mệt mỏi (S_MET_MOI)
    --[ASSOCIATED_WITH]-->
  Đau cơ (S_DAU_CO)

--- Paths Summary ---
Path 1: S_DAU_BUNG -> M_ROI_LOAN_CHUC_NANG_TE_BAO_GAN -> S_DAU_CO
Path 2: S_DAU_BUNG -> D_BENH_ADDISON -> S_MET_MOI -> S_DAU_CO  [context: D_NHIEM_VIRUS, D_VIEM_CO]
```

### Tips

| Mục tiêu | Cách dùng |
|----------|-----------|
| Tìm đường ngắn nhất | `-d 3` hoặc `-d 4` |
| Khám phá nhiều đường | `-p 20 -d 6` |
| Tránh graph quá phức tạp | `-p 5 -d 4` |
| Xem S-S context chi tiết | `--text` |

### So sánh BFS vs DFS

| Tiêu chí | BFS (hiện tại) | DFS (legacy) |
|----------|----------------|--------------|
| Đa dạng paths | ✅ Qua nhiều first-hop khác nhau | ❌ Thường đi cùng 1 hướng |
| Shortest first | ✅ Tự động (level-by-level) | ⚠️ Cần sort sau |
| S-S validation | ✅ Có | ❌ Không |

---

## Edge Types Excluded from Traversal

**QUAN TRỌNG**: Các edge types sau đây **KHÔNG** được dùng để traverse graph (mở rộng hoặc tìm đường):

| Edge Type | Lý do loại trừ |
|-----------|----------------|
| `RULES_OUT` | Quan hệ **loại trừ** - triệu chứng X loại trừ bệnh Y. Không có nghĩa đi từ X qua Y. |
| `PERTINENT_NEGATIVE` | Quan hệ **âm tính quan trọng** - sự vắng mặt của triệu chứng có ý nghĩa. |

**Hành vi:**
- `visualize_node.py`: KHÔNG traverse qua các edges này khi mở rộng graph
- `path_visualize.py`: KHÔNG dùng các edges này để tìm đường đi
- Các edges này **VẪN** được hiển thị nếu:
  - Dùng `--cross yes` trong `visualize_node.py` (tìm internal edges)
  - Nodes đã được kết nối qua các edges khác

**Ví dụ:**
```
S_DAU_NGUC --[RULES_OUT]--> D_VIEM_PHOI

Ý nghĩa: Nếu có đau ngực kiểu X, ít nghĩ đến viêm phổi
→ KHÔNG nên traverse từ S_DAU_NGUC đến D_VIEM_PHOI qua RULES_OUT
→ Nhưng VẪN hiển thị edge này nếu cả 2 nodes đều có mặt
```

---

## Design System

### 1. Node Colors (cố định theo entity type)

| Type | Màu | Hex | Ý nghĩa |
|------|-----|-----|---------|
| 🔵 **S** (Symptom) | Xanh dương | `#3B82F6` | Thông tin đầu vào từ bệnh nhân, trung tính |
| 🟠 **M** (Mechanism) | Cam | `#F59E0B` | Cơ chế sinh lý bệnh, giải thích causal |
| 🔴 **D** (Disease) | Đỏ | `#DC2626` | Chẩn đoán, quyết định lâm sàng |

**Nguyên tắc**: Màu node KHÔNG đổi theo ngữ cảnh. Người xem chỉ cần liếc là biết node thuộc loại gì.

### 2. Node Sizing

| Trạng thái | Size | Border |
|------------|------|--------|
| Center node (focus) | 35 | 4px |
| Other nodes | 22 | 2px |

### 3. Edge Direction (Arrows)

| Quan hệ | Hướng | Lý do |
|---------|-------|-------|
| D → S | có mũi tên → | Disease "có" symptom |
| M → S | có mũi tên → | Mechanism "gây ra" symptom |
| D ↔ M | không mũi tên | Definitional, hai chiều |
| M ↔ M | không mũi tên | Causal chain, context-dependent |
| S ↔ S | không mũi tên | Association, đi cùng nhau |

### 4. Edge Styles

| Quan hệ | Màu | Style | Width |
|---------|-----|-------|-------|
| **S → D SUGGESTS** | Xám `#6B7280` | Solid | 2 |
| **S → D INDICATES** | Xám đậm `#374151` | Solid | 3 |
| **S → D RULES_OUT** | Đỏ đậm `#991B1B` | Dashed | 2 |
| **M → S CAUSES** | Cam đậm `#D97706` | Solid | 3 |
| **M → S CONTRIBUTES_TO** | Cam `#F59E0B` | Dashed | 2 |
| **M → D CAUSES** | Amber đậm `#B45309` | Solid | 2 |
| **D → S HAS_SYMPTOM** | Đỏ `#DC2626` | Solid | 2 |
| **D → S PERTINENT_NEGATIVE** | Tím `#7C3AED` | Dashed | 2 |
| **D ↔ M HAS_MECHANISM** | Đỏ đậm `#B91C1C` | Solid | 2 |
| **D → D CAUSES** | Đỏ đậm `#991B1B` | Solid | 2 |
| **M → M LEADS_TO** | Amber đậm `#92400E` | Dashed | 2 |
| **S ↔ S ASSOCIATED_WITH** | Xám nhạt `#9CA3AF` | Dotted | 1.5 |

**V7 Enriched Edge Types:**
- `PERTINENT_NEGATIVE`: Câu hỏi âm tính quan trọng từ KG enrichment
- `RULES_OUT`: Triệu chứng loại trừ bệnh từ KG enrichment

### 5. Edge Tooltips

Hover vào edge để xem tooltip:
- **Edge type** và tên nodes
- **Context** (với ASSOCIATED_WITH): Lý do 2 symptoms liên quan

```
ASSOCIATED_WITH
Mệt mỏi → Hồi hộp

Liên quan:
  • Thiếu máu
  • Suy tim
  • Cường giáp
  • Rối loạn lo âu
```

**Quy tắc chung**:
- **Solid** = quan hệ primary, mạnh
- **Dashed** = quan hệ secondary, yếu hơn
- **Dotted** = association, không nhân quả

---

## Cách hoạt động

### Level Expansion

```
Level 1: Center → Neighbors trực tiếp (max N edges)
Level 2: Level 1 + Neighbors của neighbors (max N edges mỗi node)
Level 3: Level 2 + thêm 1 bậc nữa
```

### Internal Edges

Sau mỗi level, script tự động tìm thêm **internal edges** giữa các nodes đã có trong graph.

Ví dụ với center = `D_SUY_TIM`:
1. Level 1 lấy: `M_CO_THAT_PHE_QUAN`, `S_KHO_THO`, ...
2. Script tìm thêm: `M_CO_THAT_PHE_QUAN --[CAUSES]--> S_KHO_THO`

→ Graph hiển thị đầy đủ quan hệ giữa các nodes.

---

## Output Files

### HTML (default)

```bash
python visualize_node.py -e D_SUY_TIM
# Output: D_SUY_TIM_graph.html
```

Mở trong browser để:
- Kéo thả nodes
- Hover xem tooltip (node ID, edge type)
- Zoom in/out
- Click để highlight

### Text Mode

```bash
python visualize_node.py -e D_SUY_TIM --text
```

Output:
```
============================================================
Center: D_SUY_TIM
============================================================

Nodes (13):
  [D] D_SUY_TIM *
  [M] M_CO_THAT_PHE_QUAN
  [S] S_KHO_THO
  ...

Edges (29):
  D_SUY_TIM --[HAS_SYMPTOM]--> S_KHO_THO
  M_CO_THAT_PHE_QUAN --[CAUSES]--> S_KHO_THO
  ...
```

---

## Use Cases

### 1. Debug Entity Relationships

```bash
# Xem entity mới extract có đủ edges không
python visualize_node.py -e D_VIEM_PHOI -l 1 --text
```

### 2. Explore Pathophysiology

```bash
# Xem chuỗi M → M → S
python visualize_node.py -e M_GIAM_CUNG_LUONG_TIM -l 2
```

### 3. Differential Diagnosis

```bash
# Từ symptom, xem các diseases liên quan
python visualize_node.py -e S_KHO_THO -l 2
```

### 4. Disease Deep Dive

```bash
# Xem tất cả S và M của 1 disease
python visualize_node.py -e D_SUY_TIM -l 1 -E 30
```

---

## Troubleshooting

### pyvis not installed

```bash
pip install pyvis
```

### Node not found

```
Warning: Node 'X_ABC' not found in node list. Proceeding anyway...
```

→ Kiểm tra node ID có đúng format và tồn tại trong `entities/`

### Node has no edges

```
Error: Node 'X_ABC' has no edges in the graph.
```

→ Entity chưa có edges trong `edges/*.jsonl`. Cần extract thêm.

### Graph quá lớn

```bash
# Giảm edges và level
python visualize_node.py -e S_KHO_THO -l 1 -E 5
```

---

## Files liên quan

```
smd_visualization/
├── visualize_node.py      # Visualize graph từ 1 node
├── path_visualize.py      # Tìm paths giữa 2 nodes (BFS + S-S context validation)
├── update_data.py         # MERGE edges từ extracted_v5 vào data hiện tại
├── regenerate_data.py     # TẠO LẠI TOÀN BỘ data từ extracted_v5 (replace)
├── README.md              # Document này
├── all_edges.json         # Tất cả edges (JSONL)
├── S_nodes.json           # Danh sách Symptom [{id, name}]
├── M_nodes.json           # Danh sách Mechanism [{id, name}]
├── D_nodes.json           # Danh sách Disease [{id, name}]
└── *_graph.html           # Output files

extracted_v5/
├── entities/              # Entity files (S, M, D) - auto-extracted
├── entities_manual/       # Manual entities (JSONL format) - ALSO SCANNED
└── edges/                 # Edge files (*.jsonl)
```

### Data Management Scripts

| Script | Mục đích | Khi nào dùng |
|--------|----------|--------------|
| `update_data.py` | Merge data mới vào data cũ | Khi thêm entities/edges mới |
| `regenerate_data.py` | Tạo lại toàn bộ từ extracted_v5 | Khi cần reset hoặc sau enrichment |

```bash
# Merge thêm data mới
python update_data.py

# Tạo lại toàn bộ (khi entity schema thay đổi)
python regenerate_data.py
```

### Node file format

```json
[
  {"id": "S_KHO_THO", "name": "Khó thở"},
  {"id": "S_HOI_HOP", "name": "Hồi hộp"},
  {"id": "S_KHONG_CO_NAME", "name": ""}
]
```

Node có `name` → hiển thị tên tiếng Việt
Node không có `name` → hiển thị ID

---

## Nguyên tắc thiết kế (tham khảo)

1. **Entity type → màu cố định**: Không đổi màu theo ngữ cảnh
2. **Ý nghĩa lâm sàng > thẩm mỹ**: D = nặng, S = trung tính, M = trung gian
3. **Highlight ≠ recolor**: Đổi size/border, không đổi màu gốc
4. **Edge kể câu chuyện**: Màu node phân loại, edge thể hiện logic
5. **Tối đa 3 màu entity**: Thêm loại mới dùng shape/icon, không thêm màu

---

## Changelog

- **v1.7.0** (2026-02-07): **BREAKING** - Loại bỏ `RULES_OUT` và `PERTINENT_NEGATIVE` khỏi graph traversal. Các edge types này là quan hệ loại trừ/âm tính, không nên dùng để tìm đường hoặc mở rộng graph. Vẫn hiển thị khi dùng `--cross yes`.
- **v1.6.0** (2026-02-07): Thêm `regenerate_data.py` để tạo lại toàn bộ data từ extracted_v5. Thêm edge styles cho V7 enriched types: `PERTINENT_NEGATIVE`, `D→D CAUSES`, `M→D CAUSES`. Data regenerated: 1479 nodes, 6079 edges.
- **v1.5.0** (2026-02-01): `path_visualize.py` - Đổi lại sang **BFS** cho đa dạng paths, thêm **S-S context validation** (tất cả S-S edges trong path phải có chung context)
- **v1.4.0** (2026-01-31): `path_visualize.py` - Đổi từ BFS sang DFS, tìm **tất cả paths** (không chỉ shortest), thêm `--max-depth`
- **v1.3.0** (2026-01-30): Thêm `path_visualize.py` - BFS tìm đường đi ngắn nhất
- **v1.2.0** (2026-01-30): Di chuyển sang module `smd_visualization/`
- **v1.1.0** (2026-01-30): Thêm `--cross`, `--edges`, hỗ trợ level 4, node names từ *_nodes.json
- **v1.0.0** (2026-01-30): Initial version

---

*Updated: 2026-02-07 (v1.7.0)*
