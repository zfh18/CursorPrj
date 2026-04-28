# DBC 合并脚本说明

## 脚本作用

`merge_dbc.py` 用于将多个 DBC 文件合并为一个完整的 DBC 文件，主要能力包括：

- 支持任意多个输入 DBC 文件（至少 2 个）
- 自动合并 `BU_` 节点列表（去重）
- 自动合并 `BO_` 消息及其 `SG_` 信号
- 对 `CM_`、`BA_DEF_`、`BA_DEF_DEF_`、`BA_`、`VAL_` 做顺序去重
- 保持输出 DBC 编码兼容中文（优先 `GB2312`，回退 `GBK`）


## 环境要求

- Python 3.7 及以上（建议 Python 3.9+）
- 无第三方依赖，使用标准库即可运行


## 使用方法

###! 命令格式

```bash
python merge_dbc.py <输入1.dbc> <输入2.dbc> [输入3.dbc ...] -o <输出文件.dbc>
```

说明：

- 输入文件为位置参数，支持 `2..N` 个
- 输出文件使用 `-o` 或 `--output` 指定（必填）

###! 示例

```bash
# 合并 2 个文件
python merge_dbc.py A.dbc B.dbc -o Merged.dbc

# 合并多个文件
python merge_dbc.py A.dbc B.dbc C.dbc D.dbc -o Merged.dbc
```

Windows 下也可以使用绝对路径：

```bash
python "F:\CursorPrj\MergeDBC\merge_dbc.py" ^
  "F:\CursorPrj\MergeDBC\A.dbc" ^
  "F:\CursorPrj\MergeDBC\B.dbc" ^
  -o "F:\CursorPrj\MergeDBC\Merged.dbc"
```


## 参数说明

- `inputs`：输入 DBC 文件路径列表（至少 2 个）
- `-o, --output`：输出合并后的 DBC 文件路径（必填）
- `-h, --help`：查看帮助


## 合并规则

1. **基础段选择**
   - `header`、`ns`、`bs`：从输入文件中按顺序选择第一个非空段作为输出基础

2. **节点合并（`BU_`）**
   - 提取所有输入文件节点名并去重，按字母排序后输出

3. **消息合并（`BO_` + `SG_`）**
   - 对同一消息 ID：
     - 消息头使用首次出现的定义
     - 信号按信号名去重并合并（保留首次出现）

4. **注释/属性/值表**
   - `CM_`、`BA_DEF_`、`BA_DEF_DEF_`、`BA_`、`VAL_`
   - 按输入顺序去重，保证结果稳定


## 编码说明（中文不乱码）

- 读取输入文件时，脚本按以下顺序尝试：
  1. `GB2312`
  2. `GBK`
  3. `UTF-8`
- 写出文件时：
  - 优先使用 `GB2312`
  - 若编码异常，自动回退 `GBK`

这能保证大多数国产 DBC 文件中的中文注释正常显示。


## 运行输出说明

脚本运行后会打印：

- 输入文件数量及路径
- 输出文件路径
- 合并统计信息（消息、注释、属性定义、值表数量）


## 常见问题

1. **提示“至少需要提供2个输入DBC文件”**
   - 请确认命令中传入了至少两个输入文件

2. **提示“文件不存在”**
   - 请检查输入路径是否正确，建议使用绝对路径

3. **终端显示乱码**
   - Windows 终端可能显示编码不一致，但不代表输出文件损坏
   - 可在 DBC 工具中直接验证中文显示是否正常

