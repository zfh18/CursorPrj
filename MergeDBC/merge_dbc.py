#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBC文件合并工具
合并SCU_RL和SCU_RR两个节点的DBC文件
"""

import re
import os
import argparse
import sys
from collections import OrderedDict, Counter

BO_LINE_RE = re.compile(r'^BO_\s+\d+\s+')

# 用于解析信号行并拆出接收节点列表。DBC 信号行格式大致为:
#   SG_ Name [Mux] : ... "unit"  RxNode1,RxNode2
SG_LINE_RE = re.compile(r'^(?P<prefix>\s*SG_\s+(?P<name>\S+)(?:\s+\S+)?\s*:\s+.*"\s+)(?P<receivers>.+?)\s*$')

# 用于识别 NM_ 开头报文（用于推断 NmAsrBaseAddress 的范围与节点 ID）
# 捕获组: (msg_id, msg_name, transmitter)
BO_NM_RE = re.compile(r'^BO_\s+(\d+)\s+(NM_\S+?)\s*:\s*\d+\s+(\S+)')

# 当 BO_ 发送者为 Vector__XXX 占位时, 兜底用的命名解析: NM_<NodeName>[_后缀]
NM_NAME_FALLBACK_RE = re.compile(r'^NM_([A-Za-z_][A-Za-z0-9_]*)')

# DBC 标准里表示"无发送者"的占位节点名, 解析节点时应跳过
NM_TRANSMITTER_PLACEHOLDERS = {'Vector__XXX', 'Vector__Independent'}

# 用于按属性名解析/识别已有的 BA_DEF_ / BA_DEF_DEF_ 行，便于覆盖
BA_DEF_NAME_RE = re.compile(r'^BA_DEF_\s+(?:BU_\s+|BO_\s+|SG_\s+|EV_\s+)?"([^"]+)"')
BA_DEF_DEF_NAME_RE = re.compile(r'^BA_DEF_DEF_\s+"([^"]+)"')

# 用于识别网络级 BA_ "DBName" "..."; 赋值行（合并时会被替换为输出文件名）
BA_DBNAME_RE = re.compile(r'^BA_\s+"DBName"\s+')

# 用于识别多发送者行: BO_TX_BU_ <can_id> : Node1, Node2, ...;
BO_TX_BU_RE = re.compile(r'^BO_TX_BU_\s+(-?\d+)\s*:\s*([^;]+);')

# 用于识别节点级 BA_ "NmAsrNodeIdentifier" BU_ <node> ...; 行（注入前先剔除）
BA_NODE_IDENTIFIER_RE = re.compile(r'^BA_\s+"NmAsrNodeIdentifier"\s+BU_\s+')

# 找不到 NM_ 报文时 NmAsrBaseAddress 默认采用的高位段（按工程要求为 0x4xx）
NM_BASE_FALLBACK_HIGH = 0x4

# 合并时需要追加 / 覆盖的额外属性（来自工程要求）
# 字段含义:
#   scope:      ''   -> Network/Bus 级（BA_DEF_  "name" ...）
#               'BU_' -> Node 级（BA_DEF_ BU_  "name" ...）
#               其它如 'BO_'、'SG_' 同理
#   type_str:   BA_DEF_ 中类型与范围片段（不含末尾分号）
#   default:    BA_DEF_DEF_ 后的默认值字面量（字符串需自带双引号）
# 注意: HEX 类型在 DBC 中惯用十进制写最小/最大/默认值
# 特殊项: NmAsrBaseAddress / NmBaseAddress / NmStationAddress / NmMessageCount
#         的 type_str / default 会在运行时被 build_extra_attributes 按 DBC 中
#         NM_ 报文 ID 段动态覆盖, 这里写的只是占位
EXTRA_ATTRIBUTES = [
    ('',    'NmAsrBaseAddress',       'HEX 1024 1279',  '1024'),
    ('',    'NmBaseAddress',          'HEX 1024 1279',  '1024'),
    ('BU_', 'NmAsrCanMsgCycleOffset', 'INT 50 50',      '50'),
    ('',    'NmAsrCanMsgCycleTime',   'INT 500 500',    '500'),
    ('BU_', 'NmAsrCanMsgReducedTime', 'INT 20 20',      '20'),
    ('',    'NmAsrMessageCount',      'INT 0 256',      '256'),
    ('',    'NmMessageCount',         'INT 0 256',      '256'),
    ('BU_', 'NmAsrNodeIdentifier',    'HEX 0 255',      '255'),
    ('BU_', 'NmStationAddress',       'HEX 0 255',      '0'),
    ('',    'NmAsrRepeatMessageTime', 'INT 1600 1600',  '1600'),
    ('',    'NmAsrTimeoutTime',       'INT 2000 2000',  '2000'),
    ('',    'NmAsrWaitBusSleepTime',  'INT 2000 2000',  '2000'),
    ('BU_', 'NodeLayerModules',       'STRING ',
        '"ASRNM33.dll,osek_tp.dll,CANoeILNLVector.dll"'),
]


def is_bo_line(line):
    return bool(BO_LINE_RE.match(line))


def _format_ba_def(scope, name, type_str):
    if scope:
        return f'BA_DEF_ {scope} "{name}" {type_str};'
    return f'BA_DEF_  "{name}" {type_str};'


def _format_ba_def_def(name, default):
    return f'BA_DEF_DEF_  "{name}" {default};'


def parse_bo_tx_bu_map(other_lines):
    """解析 merged['other'] 中的 BO_TX_BU_ 行, 得到 can_id -> 发送节点名列表。

    与 BO_ 定义中的报文 ID 使用相同十进制整数键。若同一 ID 出现多行, 后出现的覆盖前行
    (合并去重后通常只有一行)。
    """
    out = {}
    for line in other_lines or []:
        mm = BO_TX_BU_RE.match(line.strip())
        if not mm:
            continue
        pid = int(mm.group(1))
        names = [x.strip() for x in mm.group(2).split(',') if x.strip()]
        out[pid] = names
    return out


def resolve_node_from_nm_message_name(msg_name, node_set):
    """从 NM_<后缀> 报文名在 BU_ 列表中解析逻辑节点名 (最长前缀匹配)。"""
    if not msg_name.startswith('NM_'):
        return None
    suffix = msg_name[3:]
    if not suffix:
        return None
    parts = suffix.split('_')
    for i in range(len(parts), 0, -1):
        candidate = '_'.join(parts[:i])
        if candidate in node_set:
            return candidate
    return None


def _fallback_nm_nodes(msg_name, transmitter, node_set):
    """无 BO_TX_BU_ 行时, 用报文名 + BO_ 发送者推断参与 NM 的节点列表 (有序去重)。"""
    ordered = []
    seen = set()

    def _add(n):
        if n and n not in seen and n in node_set:
            seen.add(n)
            ordered.append(n)

    nn = resolve_node_from_nm_message_name(msg_name, node_set)
    if nn:
        _add(nn)
    if transmitter and transmitter not in NM_TRANSMITTER_PLACEHOLDERS:
        _add(transmitter)
    if not ordered:
        m = NM_NAME_FALLBACK_RE.match(msg_name)
        if m:
            _add(m.group(1))
    return tuple(ordered)


def collect_nm_messages(merged):
    """从合并结果中提取所有 NM_ 开头报文的 (msg_id, msg_name, transmitter_nodes)。

    msg_id 为屏蔽扩展帧标志后的 11 位标准 CAN ID, 用于段推断与低字节计算。
    transmitter_nodes 为应写入相同 NmAsrNodeIdentifier 的 BU_ 节点名元组:
      - 若存在 BO_TX_BU_ <id> : A, B; 则优先采用其中的全部节点 (过滤占位符)
      - 否则回退到报文名最长前缀匹配 + BO_ 发送者等逻辑
    """
    node_set = _extract_node_set(merged)
    bo_tx = parse_bo_tx_bu_map(merged.get('other'))
    results = []
    for lines in merged['bo'].values():
        if not lines:
            continue
        m = BO_NM_RE.match(lines[0])
        if not m:
            continue
        raw_id = int(m.group(1))
        msg_id = raw_id & 0x7FF
        msg_name = m.group(2)
        transmitter = m.group(3)

        if raw_id in bo_tx:
            nodes = []
            for n in bo_tx[raw_id]:
                if n in NM_TRANSMITTER_PLACEHOLDERS:
                    continue
                if n not in node_set:
                    print(
                        f"  [NmAsrNodeIdentifier] 警告: BO_TX_BU_ {raw_id} 中的节点 {n} "
                        f"不在 BU_ 列表中 (报文 {msg_name}), 已忽略"
                    )
                    continue
                nodes.append(n)
            transmitter_nodes = tuple(sorted(set(nodes)))
            if not transmitter_nodes:
                transmitter_nodes = _fallback_nm_nodes(msg_name, transmitter, node_set)
                if transmitter_nodes:
                    print(
                        f"  [NmAsrNodeIdentifier] 提示: 报文 {msg_name} (ID={raw_id}) 的 BO_TX_BU_ "
                        f"无有效节点, 已回退到报文名/发送者推断: {', '.join(transmitter_nodes)}"
                    )
        else:
            transmitter_nodes = _fallback_nm_nodes(msg_name, transmitter, node_set)

        results.append((msg_id, msg_name, transmitter_nodes))
    return results


def detect_nm_base_address(nm_messages):
    """根据 NM_ 报文 ID 推断 NmAsrBaseAddress 的范围与默认值。

    规则:
      - NM_ 报文 ID 落在 0x?xx 段 -> 范围 0x?00..0x?FF, 默认 0x?00
      - 找不到 NM_ 报文 -> 按工程约定回退到 0x4xx 段
      - 跨多个高位段 -> 取出现次数最多的段, 并打印告警

    返回 (range_low, range_high, default, segment), 前三者为完整地址, segment 为高位段号(0..7)。
    """
    high_bytes = [msg_id >> 8 for msg_id, _, _ in nm_messages]

    if not high_bytes:
        print(f"  [NmAsrBaseAddress] 未找到 NM_ 开头报文, 回退到 0x{NM_BASE_FALLBACK_HIGH:X}xx 段")
        high = NM_BASE_FALLBACK_HIGH
    else:
        counter = Counter(high_bytes)
        unique = sorted(counter.keys())
        if len(unique) > 1:
            segments = ', '.join(f'0x{h:X}xx' for h in unique)
            high = counter.most_common(1)[0][0]
            print(f"  [NmAsrBaseAddress] 警告: NM_ 报文 ID 跨多个段 ({segments}), 按多数决采用 0x{high:X}xx")
        else:
            high = unique[0]

    base = high << 8
    return base, base | 0xFF, base, high


def build_extra_attributes(base_low, base_high, base_default):
    """基于推断出的 NmAsrBaseAddress 构建注入用的属性表。

    NmAsrBaseAddress / NmBaseAddress 使用完整 NM 基地址范围, 例如 0x400..0x4FF。
    NmStationAddress 使用该范围内的低 8 位地址, 因此固定为 0x00..0xFF。
    NmMessageCount 使用 NmStationAddress 的整数数量作为上限, 默认值为该数量。
    """
    station_low = base_low & 0xFF
    station_high = base_high & 0xFF
    station_count = station_high - station_low + 1

    extras = []
    for entry in EXTRA_ATTRIBUTES:
        scope, name, type_str, default = entry
        if name in {'NmAsrBaseAddress', 'NmBaseAddress'}:
            extras.append((scope, name, f'HEX {base_low} {base_high}', str(base_default)))
        elif name == 'NmStationAddress':
            extras.append((scope, name, f'HEX {station_low} {station_high}', str(station_low)))
        elif name == 'NmMessageCount':
            extras.append((scope, name, f'INT 0 {station_count}', str(station_count)))
        else:
            extras.append(entry)
    return extras


def _extract_node_set(merged):
    """从 merged['bu'] 解析出节点名集合, 用于校验 NM 报文映射的节点。"""
    nodes = set()
    for line in merged['bu']:
        if ':' in line:
            nodes.update(line.split(':', 1)[1].strip().split())
    return nodes


def detect_node_identifiers(nm_messages, base_segment, node_set):
    """根据 NM_ 报文为每个节点推断 NmAsrNodeIdentifier。

    每条 NM 报文可对应多个 BU_ 节点 (见 BO_TX_BU_ 多发送者), 这些节点写入相同的
    node_id (= 报文 CAN ID 低 8 位)。

    映射策略 (在 collect_nm_messages 中完成):
      - 优先 BO_TX_BU_ <can_id> 列出的全部发送节点
      - 否则报文名最长前缀匹配 BU_ + BO_ 发送者 + 单次 NM_<token> 兜底

    校验:
      - 节点必须存在于 BU_: 列表中
      - 报文 ID 高位段必须等于全局 base_segment
      - 同一节点被两条不同 NM 报文赋予不同 node_id -> 告警, 保留首次
    """
    node_id_map = OrderedDict()

    for msg_id, msg_name, transmitter_nodes in nm_messages:
        if (msg_id >> 8) != base_segment:
            print(f"  [NmAsrNodeIdentifier] 警告: 报文 {msg_name} (ID=0x{msg_id:X}) 不在 0x{base_segment:X}xx 段, 跳过")
            continue

        if not transmitter_nodes:
            print(f"  [NmAsrNodeIdentifier] 警告: 无法识别 {msg_name} (ID=0x{msg_id:X}) 对应的节点, 跳过")
            continue

        node_id = msg_id & 0xFF

        if len(transmitter_nodes) > 1:
            print(
                f"  [NmAsrNodeIdentifier] 提示: {msg_name} (ID=0x{msg_id:X}) 多发送者共用 node_id=0x{node_id:02X}: "
                f"{', '.join(sorted(transmitter_nodes))}"
            )

        for node in sorted(transmitter_nodes):
            if node not in node_set:
                continue
            if node in node_id_map:
                existing = node_id_map[node]
                if existing == node_id:
                    continue
                print(
                    f"  [NmAsrNodeIdentifier] 警告: 节点 {node} 已有 NM 推导值 0x{existing:02X}, "
                    f"忽略 {msg_name} 的 0x{node_id:02X}"
                )
                continue
            node_id_map[node] = node_id

    sorted_map = OrderedDict(sorted(node_id_map.items()))
    unmapped = sorted(node_set - set(sorted_map.keys()))
    if unmapped:
        print(
            f"  [NmAsrNodeIdentifier] 提示: 以下 BU_ 节点无对应 NM 报文可推导 ID, "
            f"不写 BA_ 行、仍用全局默认 0xFF: {', '.join(unmapped)}"
        )
    return sorted_map


def apply_node_identifier_overrides(merged, node_id_map):
    """注入/覆盖 BA_ "NmAsrNodeIdentifier" BU_ <node> <id>; 行。

    与 DBName 处理一致: 先剔除原有所有节点级 NodeIdentifier 赋值, 再追加新的,
    达到"覆盖"效果。未识别到 NM 报文的节点保持全局默认值 (255), 不写 BA_ 行。
    """
    before = len(merged['ba'])
    merged['ba'] = [line for line in merged['ba'] if not BA_NODE_IDENTIFIER_RE.match(line)]
    removed = before - len(merged['ba'])

    for node, node_id in node_id_map.items():
        merged['ba'].append(f'BA_ "NmAsrNodeIdentifier" BU_ {node} {node_id};')

    if node_id_map:
        summary = ', '.join(f'{n}=0x{i:02X}' for n, i in node_id_map.items())
        print(f"  [NmAsrNodeIdentifier] 已为 {len(node_id_map)} 个节点注入: {summary} (清除原有 {removed} 条)")
    else:
        print(f"  [NmAsrNodeIdentifier] 未识别到任何节点 NM 报文, 全部走默认值 (清除原有 {removed} 条)")


def apply_extra_attributes(merged, extras):
    """向合并结果注入额外属性定义与默认值。

    若同名属性已存在（例如 NodeLayerModules），则先剔除原 BA_DEF_ 与
    BA_DEF_DEF_ 行，再追加新的，达到“覆盖”效果；否则直接追加新增。
    其余未涉及的属性条目保持原顺序不变。
    """
    extra_names = {name for _, name, _, _ in extras}

    def _name_in_extras(regex, line):
        m = regex.match(line)
        return bool(m) and m.group(1) in extra_names

    merged['ba_def'] = [
        line for line in merged['ba_def']
        if not _name_in_extras(BA_DEF_NAME_RE, line)
    ]
    merged['ba_def_def'] = [
        line for line in merged['ba_def_def']
        if not _name_in_extras(BA_DEF_DEF_NAME_RE, line)
    ]

    for scope, name, type_str, default in extras:
        merged['ba_def'].append(_format_ba_def(scope, name, type_str))
        merged['ba_def_def'].append(_format_ba_def_def(name, default))


def _derive_dbname_from_path(output_path):
    """从输出文件路径推导用作 DBName 的字符串：取文件名并去掉 .dbc 扩展。"""
    base = os.path.basename(output_path)
    stem, ext = os.path.splitext(base)
    if ext.lower() == '.dbc':
        return stem
    return base


def apply_dbname_override(merged, output_path):
    """将合并后的 BA_ "DBName" 赋值统一替换为输出文件名。

    多个输入 DBC 通常各自带有不同的 BA_ "DBName" 赋值，合并去重后会
    在输出中残留多条，违反 DBC 规范（Network 级属性只能赋值一次）。
    这里先剔除所有原 BA_ "DBName" 行，再追加一条以输出文件名为值的赋值。
    """
    db_name = _derive_dbname_from_path(output_path)

    before = len(merged['ba'])
    merged['ba'] = [line for line in merged['ba'] if not BA_DBNAME_RE.match(line)]
    removed = before - len(merged['ba'])

    merged['ba'].append(f'BA_ "DBName" "{db_name}";')

    print(f"  [DBName] 已用输出文件名覆盖: \"{db_name}\" (清除原有 {removed} 条)")


def parse_dbc_file(filepath):
    """解析DBC文件"""
    # 尝试使用GB2312编码读取，如果失败则使用utf-8
    try:
        with open(filepath, 'r', encoding='gb2312', errors='ignore') as f:
            content = f.read()
    except (UnicodeDecodeError, LookupError):
        # 如果GB2312失败，尝试GBK（GB2312的超集）
        try:
            with open(filepath, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()
        except (UnicodeDecodeError, LookupError):
            # 最后尝试utf-8
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    
    result = {
        'header': [],
        'ns': [],
        'bs': [],
        'bu': [],
        'bo': OrderedDict(),  # 使用OrderedDict保持顺序
        'cm': [],
        'ba_def': [],
        'ba_def_def': [],
        'ba': [],
        'val': [],
        'other': []
    }
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
            
        # 解析头部
        if line.startswith('VERSION'):
            result['header'].append(line)
        elif line.startswith('NS_'):
            result['ns'].append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('BS_'):
                if lines[i].strip():
                    result['ns'].append(lines[i].strip())
                i += 1
            continue
        elif line.startswith('BS_'):
            result['bs'].append(line)
        elif line.startswith('BU_:'):
            # 解析节点列表
            result['bu'].append(line)
        elif is_bo_line(line):
            # 解析消息定义
            parts = line.split()
            if len(parts) < 2:
                i += 1
                continue
            msg_id = parts[1]
            result['bo'][msg_id] = [line]
            i += 1
            while i < len(lines):
                next_line_raw = lines[i]
                next_line = next_line_raw.strip()
                if not next_line:
                    i += 1
                    continue
                # 检查是否是信号行（前面可能有空格）
                if next_line.startswith('SG_') or next_line_raw.startswith(' SG_'):
                    result['bo'][msg_id].append(next_line_raw.rstrip('\n\r'))
                    i += 1
                elif is_bo_line(next_line) or next_line.startswith('BO_TX_BU_') or \
                     next_line.startswith('CM_') or next_line.startswith('BA_') or \
                     next_line.startswith('VAL_') or next_line.startswith('BA_DEF_'):
                    break
                else:
                    # 遇到非SG_的顶层语句，交给外层解析，避免吞掉有效行
                    break
            continue
        elif line.startswith('CM_'):
            # 处理CM_注释，可能是多行的
            cm_line = line
            i += 1
            # 如果CM_行以引号开始但没有以";结束，说明是多行注释
            if '"' in line and not line.rstrip().endswith('";'):
                # 继续读取直到找到结束的";
                while i < len(lines):
                    next_line = lines[i].rstrip('\n\r')
                    cm_line += '\n' + next_line
                    i += 1
                    if next_line.strip().endswith('";'):
                        break
            result['cm'].append(cm_line)
            continue
        elif line.startswith('BA_DEF_DEF_'):
            result['ba_def_def'].append(line)
        elif line.startswith('BA_DEF_'):
            result['ba_def'].append(line)
        elif line.startswith('BA_'):
            result['ba'].append(line)
        elif line.startswith('VAL_'):
            result['val'].append(line)
        else:
            result['other'].append(line)
        
        i += 1
    
    return result

def merge_bu_nodes(bu_lists):
    """合并多个DBC中的节点列表"""
    all_nodes = set()
    for bu in bu_lists:
        if not bu:
            continue
        line = bu[0]
        if ':' in line:
            all_nodes.update(line.split(':', 1)[1].strip().split())
    return [f"BU_: {' '.join(sorted(all_nodes))}"] if all_nodes else []


def dedupe_append(items, seen, output):
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)


def normalize_dbc_spacing(line):
    """压缩引号外空白，用于判断 DBC 定义行是否仅格式不同。"""
    out = []
    in_quote = False
    last_was_space = False
    for ch in line.strip():
        if ch == '"':
            in_quote = not in_quote
            out.append(ch)
            last_was_space = False
        elif ch.isspace() and not in_quote:
            if not last_was_space:
                out.append(' ')
                last_was_space = True
        else:
            out.append(ch)
            last_was_space = False
    return ''.join(out)


def dedupe_attribute_definitions(items, regex, seen_by_name, unmatched_seen, output, label):
    """按属性名去重 BA_DEF_ / BA_DEF_DEF_，避免空白差异导致重复定义。"""
    for item in items:
        m = regex.match(item)
        if not m:
            if item not in unmatched_seen:
                unmatched_seen.add(item)
                output.append(item)
            continue

        name = m.group(1)
        normalized = normalize_dbc_spacing(item)
        if name in seen_by_name:
            if seen_by_name[name] != normalized:
                print(
                    f'  [AttributeMerge] 警告: {label} "{name}" 存在不同定义, '
                    '已保留首次出现的定义'
                )
            continue

        seen_by_name[name] = normalized
        output.append(item)


def parse_signal_line(line):
    """拆分 SG_ 行，返回 (signal_name, prefix_without_receivers, receivers)。

    prefix 保留原有格式并包含接收节点前的空白，便于在合并 receiver 后重建
    信号行。无法识别时返回 None。
    """
    m = SG_LINE_RE.match(line.rstrip('\n\r'))
    if not m:
        return None
    receivers = [x.strip() for x in m.group('receivers').split(',') if x.strip()]
    return m.group('name'), m.group('prefix'), receivers


def merge_signal_receivers(existing, incoming, msg_id):
    """合并两条同名 SG_ 行的 receiver 列表。

    若除 receiver 外的信号结构不同，保留首次出现的定义并打印告警；否则
    按输入顺序追加新 receiver，避免 RX 报文在多节点 DBC 合并时丢失接收方。
    """
    existing_parsed = parse_signal_line(existing)
    incoming_parsed = parse_signal_line(incoming)

    if not existing_parsed or not incoming_parsed:
        return existing

    sig_name, existing_prefix, existing_receivers = existing_parsed
    _, incoming_prefix, incoming_receivers = incoming_parsed

    if existing_prefix.strip() != incoming_prefix.strip():
        print(
            f"  [SignalMerge] 警告: 报文 {msg_id} 的信号 {sig_name} 存在不同定义, "
            "已保留首次出现的定义"
        )
        return existing

    merged_receivers = []
    seen = set()
    for receiver in existing_receivers + incoming_receivers:
        if receiver not in seen:
            seen.add(receiver)
            merged_receivers.append(receiver)

    return existing_prefix + ','.join(merged_receivers)


def write_merged_content(f, merged):
    # 写入头部
    for line in merged['header']:
        f.write(line + '\n')
    f.write('\n\n')

    # 写入命名空间
    for line in merged['ns']:
        f.write(line + '\n')
    f.write('\n')

    # 写入BS
    for line in merged['bs']:
        f.write(line + '\n')
    f.write('\n')

    # 写入节点列表
    for line in merged['bu']:
        f.write(line + '\n')
    f.write('\n\n')

    # 写入消息定义
    for msg_id in sorted(merged['bo'].keys(), key=int):
        for line in merged['bo'][msg_id]:
            f.write(line + '\n')
        f.write('\n')

    # 写入其他顶层语句（如 BO_TX_BU_）
    if merged['other']:
        for line in merged['other']:
            f.write(line + '\n')
        f.write('\n')

    # 写入注释
    for line in merged['cm']:
        f.write(line + '\n')
    if merged['cm']:
        f.write('\n')

    # 写入属性定义
    for line in merged['ba_def']:
        f.write(line + '\n')
    if merged['ba_def']:
        f.write('\n')

    # 写入属性默认值
    for line in merged['ba_def_def']:
        f.write(line + '\n')
    if merged['ba_def_def']:
        f.write('\n')

    # 写入属性
    for line in merged['ba']:
        f.write(line + '\n')
    if merged['ba']:
        f.write('\n')

    # 写入值表
    for line in merged['val']:
        f.write(line + '\n')


def merge_dbc_files(input_paths, output_path):
    """合并多个DBC文件"""
    parsed_dbcs = []
    for path in input_paths:
        print(f"正在解析 {path}...")
        parsed_dbcs.append(parse_dbc_file(path))

    if len(parsed_dbcs) == 1:
        print("正在归一化（单文件模式）...")
    else:
        print("正在合并...")

    def first_non_empty(key):
        for dbc in parsed_dbcs:
            if dbc[key]:
                return dbc[key]
        return []

    merged = {
        'header': first_non_empty('header'),
        'ns': first_non_empty('ns'),
        'bs': first_non_empty('bs'),
        'bu': merge_bu_nodes([dbc['bu'] for dbc in parsed_dbcs]),
        'bo': OrderedDict(),
        'cm': [],
        'ba_def': [],
        'ba_def_def': [],
        'ba': [],
        'val': [],
        'other': []
    }

    # 合并消息(BO_)，同一消息ID下合并所有信号并按信号名去重
    all_msg_ids = set()
    for dbc in parsed_dbcs:
        all_msg_ids.update(dbc['bo'].keys())

    for msg_id in sorted(all_msg_ids, key=int):
        msg_header = None
        signal_dict = {}
        for dbc in parsed_dbcs:
            msg = dbc['bo'].get(msg_id)
            if not msg:
                continue
            if msg_header is None:
                msg_header = msg[0]
            for sig in msg[1:]:
                sig_stripped = sig.strip()
                if sig_stripped.startswith('SG_'):
                    parsed_sig = parse_signal_line(sig)
                    if parsed_sig:
                        sig_name = parsed_sig[0]
                        if sig_name not in signal_dict:
                            signal_dict[sig_name] = sig
                        else:
                            signal_dict[sig_name] = merge_signal_receivers(
                                signal_dict[sig_name], sig, msg_id
                            )
        if msg_header is not None:
            merged['bo'][msg_id] = [msg_header] + list(signal_dict.values())

    # 合并注释/属性/值表，保持顺序去重
    cm_set = set()
    ba_def_seen = {}
    ba_def_unmatched_set = set()
    ba_def_def_seen = {}
    ba_def_def_unmatched_set = set()
    ba_set = set()
    val_set = set()
    other_set = set()
    for dbc in parsed_dbcs:
        dedupe_append(dbc['cm'], cm_set, merged['cm'])
        dedupe_attribute_definitions(
            dbc['ba_def'], BA_DEF_NAME_RE, ba_def_seen,
            ba_def_unmatched_set, merged['ba_def'], 'BA_DEF_'
        )
        dedupe_attribute_definitions(
            dbc['ba_def_def'], BA_DEF_DEF_NAME_RE, ba_def_def_seen,
            ba_def_def_unmatched_set, merged['ba_def_def'], 'BA_DEF_DEF_'
        )
        dedupe_append(dbc['ba'], ba_set, merged['ba'])
        dedupe_append(dbc['val'], val_set, merged['val'])
        dedupe_append(dbc['other'], other_set, merged['other'])

    # 注入/覆盖工程要求的额外属性（如 Nm/NmAsr* 与 NodeLayerModules）
    # NmAsrBaseAddress 的范围由当前 DBC 内 NM_ 开头报文的 ID 段动态决定
    nm_messages = collect_nm_messages(merged)
    base_low, base_high, base_default, base_segment = detect_nm_base_address(nm_messages)
    print(f"  [NmAsrBaseAddress] 推断范围: 0x{base_low:X}..0x{base_high:X}, 默认: 0x{base_default:X}")
    apply_extra_attributes(merged, build_extra_attributes(base_low, base_high, base_default))

    # 按各节点的 NM 报文低字节注入 NmAsrNodeIdentifier 的节点级赋值
    node_id_map = detect_node_identifiers(nm_messages, base_segment, _extract_node_set(merged))
    apply_node_identifier_overrides(merged, node_id_map)

    # 用输出文件名覆盖 DBName，避免多份输入残留多条 BA_ "DBName"
    apply_dbname_override(merged, output_path)

    print(f"正在写入合并后的文件: {output_path}")
    try:
        with open(output_path, 'w', encoding='gb2312', errors='replace') as f:
            write_merged_content(f, merged)
    except UnicodeEncodeError:
        with open(output_path, 'w', encoding='gbk', errors='replace') as f:
            write_merged_content(f, merged)
    
    print(f"合并完成! 输出文件: {output_path}")
    print(f"合并统计:")
    print(f"  - 消息数量: {len(merged['bo'])}")
    print(f"  - 注释数量: {len(merged['cm'])}")
    print(f"  - 属性定义数量: {len(merged['ba_def'])}")
    print(f"  - 值表数量: {len(merged['val'])}")
    print(f"  - 注入额外属性: {len(EXTRA_ATTRIBUTES)} 条")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='DBC文件合并/归一化工具 - 合并任意多个DBC文件；单输入时执行归一化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 多文件合并
  python merge_dbc.py a.dbc b.dbc -o merged.dbc
  python merge_dbc.py a.dbc b.dbc c.dbc d.dbc -o merged.dbc

  # 单文件归一化（重排序 / 去重 / 注入 NM 相关属性 / 覆盖 DBName）
  python merge_dbc.py a.dbc -o a_normalized.dbc
        '''
    )

    parser.add_argument(
        'inputs',
        nargs='+',
        help='输入DBC文件路径列表，支持任意多个（至少1个；为1个时执行单文件归一化）'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='输出合并后的DBC文件路径'
    )

    args = parser.parse_args()

    if len(args.inputs) < 1:
        print("错误: 至少需要提供1个输入DBC文件。")
        sys.exit(1)

    # 检查输入文件是否存在
    for input_path in args.inputs:
        if not os.path.exists(input_path):
            print(f"错误: 文件不存在: {input_path}")
            sys.exit(1)

    if len(args.inputs) == 1:
        print("模式: 单文件归一化（重排序 / 去重 / 注入 NM 相关属性 / 覆盖 DBName）")
    else:
        print(f"模式: 多文件合并 ({len(args.inputs)} 个输入)")
    for idx, input_path in enumerate(args.inputs, start=1):
        print(f"输入文件{idx}: {input_path}")
    print(f"输出文件: {args.output}")
    print()

    merge_dbc_files(args.inputs, args.output)
