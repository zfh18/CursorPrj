# -*- coding: utf-8 -*-
import re

# 读取HTML文件
with open('LPAC014-APP-静态扫描报告-ASW.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# 查找所有severity相关的ID
severity_ids = re.findall(r'severity_(\d+)', html_content, re.IGNORECASE)
unique_severities = sorted(set(int(s) for s in severity_ids))
print(f"找到的Severity值: {unique_severities}")
print(f"需要删除的Severity (>=6): {[s for s in unique_severities if s >= 6]}")

# 尝试找到severity块的开始和结束
# 看起来结构是：一个severity行，然后是一个child_group_row，里面包含所有子项
# 我们需要找到从severity行开始到下一个severity行（或结束）之间的所有内容

# 查找所有severity行的位置
severity_pattern = r'<tr[^>]*id=[\'"]warning_summary_table_severity_(\d+)[^>]*>'
matches = list(re.finditer(severity_pattern, html_content, re.IGNORECASE))

print(f"\n找到 {len(matches)} 个severity行")
for match in matches[:5]:
    severity_num = match.group(1)
    start = match.start()
    # 查看这个severity行的内容
    end_pos = min(len(html_content), start + 500)
    print(f"\nSeverity {severity_num} 行开始位置: {start}")
    print(f"内容预览: {html_content[start:end_pos][:200]}")

# 查找child_group_row的位置
child_pattern = r'<tr[^>]*id=[\'"]warning_summary_table_severity_(\d+)_child_group_row[^>]*>'
child_matches = list(re.finditer(child_pattern, html_content, re.IGNORECASE))
print(f"\n找到 {len(child_matches)} 个child_group_row")
for match in child_matches[:3]:
    severity_num = match.group(1)
    start = match.start()
    end_pos = min(len(html_content), start + 300)
    print(f"\nSeverity {severity_num} child_group_row 位置: {start}")
    print(f"内容预览: {html_content[start:end_pos][:200]}")
