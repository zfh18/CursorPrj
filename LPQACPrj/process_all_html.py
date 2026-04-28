# -*- coding: utf-8 -*-
import re
import glob
import os
import sys

def get_all_severities(html_files):
    """
    从所有HTML文件中获取所有可用的Severity值
    """
    all_severities = set()
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            severity_ids = re.findall(r'severity_(\d+)', content, re.IGNORECASE)
            all_severities.update(int(s) for s in severity_ids)
        except Exception as e:
            print(f"Error reading {html_file}: {e}")
    return sorted(all_severities)

def remove_severity_blocks(html_content, severities_to_remove):
    """
    删除指定Severity值的块
    severities_to_remove: 要删除的Severity值列表
    """
    if not severities_to_remove:
        return html_content, 0
    
    result = html_content
    total_removed = 0
    
    # 对每个需要删除的severity，找到并删除所有相关内容
    for severity in sorted(severities_to_remove):
        # 查找所有包含severity_X的位置
        severity_positions = []
        for match in re.finditer(rf'severity_{severity}', result, re.IGNORECASE):
            severity_positions.append(match.start())
        
        # 对于每个位置，找到包含它的完整tr块
        blocks_to_remove = []
        for pos in severity_positions:
            # 向前查找最近的<tr
            before = result[:pos]
            tr_start = before.rfind('<tr')
            if tr_start == -1:
                continue
            
            # 向后查找匹配的</tr>
            after = result[tr_start:]
            depth = 0
            tr_end = -1
            i = 0
            while i < len(after):
                next_tr = after.find('<tr', i)
                next_tr_end = after.find('</tr>', i)
                
                if next_tr_end == -1:
                    break
                
                if next_tr != -1 and next_tr < next_tr_end:
                    depth += 1
                    i = next_tr + 3
                else:
                    depth -= 1
                    if depth == 0:
                        tr_end = tr_start + next_tr_end + 5
                        break
                    i = next_tr_end + 5
            
            if tr_end != -1:
                blocks_to_remove.append((tr_start, tr_end))
        
        # 合并重叠的块
        if blocks_to_remove:
            blocks_to_remove.sort()
            merged_blocks = []
            current_start, current_end = blocks_to_remove[0]
            for start, end in blocks_to_remove[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    merged_blocks.append((current_start, current_end))
                    current_start, current_end = start, end
            merged_blocks.append((current_start, current_end))
            
            # 从后向前删除，避免位置偏移
            for start, end in reversed(merged_blocks):
                removed_size = end - start
                result = result[:start] + result[end:]
                total_removed += removed_size
    
    return result, total_removed

if __name__ == '__main__':
    # 设置输出编码（Windows）
    if sys.platform == 'win32':
        import io
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except:
            pass
    
    # 查找所有HTML文件
    html_files = glob.glob('*.html')
    
    if not html_files:
        print("未找到HTML文件")
        exit(1)
    
    print(f"找到 {len(html_files)} 个HTML文件:")
    for i, f in enumerate(html_files, 1):
        print(f"  {i}. {f}")
    
    # 获取所有可用的Severity值
    print("\n正在扫描所有文件中的Severity值...")
    all_severities = get_all_severities(html_files)
    
    if not all_severities:
        print("未找到任何Severity值")
        exit(1)
    
    print(f"\n找到以下Severity值: {all_severities}")
    
    # 交互式选择要删除的Severity
    print("\n请选择要删除的Severity值（输入数字，多个用逗号或空格分隔，例如: 6,7,8 或 6 7 8）")
    print("输入 'all' 删除所有，输入 'none' 或直接回车取消操作")
    
    try:
        user_input = input("请输入: ").strip()
    except:
        print("\n操作已取消")
        exit(0)
    
    if user_input.lower() in ['none', '']:
        print("操作已取消")
        exit(0)
    
    if user_input.lower() == 'all':
        severities_to_remove = all_severities
    else:
        # 解析输入
        severities_to_remove = []
        # 支持逗号或空格分隔
        parts = re.split(r'[,，\s]+', user_input)
        for part in parts:
            part = part.strip()
            if part.isdigit():
                severity = int(part)
                if severity in all_severities:
                    severities_to_remove.append(severity)
                else:
                    print(f"警告: Severity {severity} 不在可用列表中，已忽略")
        
        if not severities_to_remove:
            print("未选择任何有效的Severity值，操作已取消")
            exit(0)
    
    severities_to_remove = sorted(set(severities_to_remove))
    print(f"\n将删除以下Severity值: {severities_to_remove}")
    
    # 确认
    try:
        confirm = input("确认删除? (y/n): ").strip().lower()
    except:
        print("\n操作已取消")
        exit(0)
    
    if confirm not in ['y', 'yes', '是', '确认']:
        print("操作已取消")
        exit(0)
    
    # 处理所有文件
    print(f"\n开始处理 {len(html_files)} 个文件...")
    
    for html_file in html_files:
        print(f"\n处理: {html_file}")
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            original_size = len(html_content)
            print(f"  原始大小: {original_size:,} 字符")
            
            filtered_content, removed_size = remove_severity_blocks(html_content, severities_to_remove)
            
            print(f"  删除: {removed_size:,} 字符")
            print(f"  新大小: {len(filtered_content):,} 字符")
            
            # 保存到原文件（覆盖）
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(filtered_content)
            
            print(f"  已保存: {html_file}")
        except Exception as e:
            print(f"  错误: {e}")
    
    print("\n完成！")
