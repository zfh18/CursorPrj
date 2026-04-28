#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBC文件合并工具
合并SCU_RL和SCU_RR两个节点的DBC文件
"""

import re
import argparse
import sys
from collections import OrderedDict

BO_LINE_RE = re.compile(r'^BO_\s+\d+\s+')


def is_bo_line(line):
    return bool(BO_LINE_RE.match(line))


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
        elif line.startswith('BA_DEF_'):
            result['ba_def'].append(line)
        elif line.startswith('BA_DEF_DEF_'):
            result['ba_def_def'].append(line)
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
                    parts = sig_stripped.split()
                    if len(parts) >= 2:
                        sig_name = parts[1]
                        if sig_name not in signal_dict:
                            signal_dict[sig_name] = sig
        if msg_header is not None:
            merged['bo'][msg_id] = [msg_header] + list(signal_dict.values())

    # 合并注释/属性/值表，保持顺序去重
    cm_set = set()
    ba_def_set = set()
    ba_def_def_set = set()
    ba_set = set()
    val_set = set()
    other_set = set()
    for dbc in parsed_dbcs:
        dedupe_append(dbc['cm'], cm_set, merged['cm'])
        dedupe_append(dbc['ba_def'], ba_def_set, merged['ba_def'])
        dedupe_append(dbc['ba_def_def'], ba_def_def_set, merged['ba_def_def'])
        dedupe_append(dbc['ba'], ba_set, merged['ba'])
        dedupe_append(dbc['val'], val_set, merged['val'])
        dedupe_append(dbc['other'], other_set, merged['other'])

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='DBC文件合并工具 - 合并任意多个DBC文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python merge_dbc.py a.dbc b.dbc -o merged.dbc
  python merge_dbc.py a.dbc b.dbc c.dbc d.dbc -o merged.dbc
        '''
    )

    parser.add_argument(
        'inputs',
        nargs='+',
        help='输入DBC文件路径列表，支持任意多个（至少2个）'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='输出合并后的DBC文件路径'
    )

    args = parser.parse_args()

    if len(args.inputs) < 2:
        print("错误: 至少需要提供2个输入DBC文件。")
        sys.exit(1)

    # 检查输入文件是否存在
    import os
    for input_path in args.inputs:
        if not os.path.exists(input_path):
            print(f"错误: 文件不存在: {input_path}")
            sys.exit(1)

    print(f"输入文件数量: {len(args.inputs)}")
    for idx, input_path in enumerate(args.inputs, start=1):
        print(f"输入文件{idx}: {input_path}")
    print(f"输出文件: {args.output}")
    print()

    merge_dbc_files(args.inputs, args.output)
