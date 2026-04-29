# DBC 合并 / 归一化脚本说明

## 脚本作用

`merge_dbc.py` 用于将多个 DBC 文件合并为一个完整的 DBC 文件；当只传入 1 个输入时，会以同一套规则对单个文件执行**归一化**处理，主要能力包括：

- 支持任意多个输入 DBC 文件（**至少 1 个**；为 1 个时执行单文件归一化）
- 自动合并 `BU_` 节点列表（去重并按字母排序）
- 自动合并 `BO_` 消息及其 `SG_` 信号（同名信号去重）
- 对 `CM_`、`BA_DEF_`、`BA_DEF_DEF_`、`BA_`、`VAL_` 做顺序去重
- 自动注入 / 覆盖工程要求的 `NmAsr*` 与 `NodeLayerModules` 等额外属性
- `NmAsrBaseAddress` 范围根据 DBC 中 `NM_` 报文 ID 段动态推断
- `NmAsrNodeIdentifier` 按各节点的 `NM_` 报文 ID 低字节自动写入节点级赋值
- `BA_ "DBName"` 自动改写为输出文件名（避免多输入残留多条 `DBName`）
- 保持输出 DBC 编码兼容中文（优先 `GB2312`，回退 `GBK`）


## 环境要求

- Python 3.7 及以上（建议 Python 3.9+）
- 无第三方依赖，使用标准库即可运行


## 使用方法

### 命令格式

```bash
python merge_dbc.py <输入1.dbc> [输入2.dbc ...] -o <输出文件.dbc>
```

说明：

- 输入文件为位置参数，支持 `1..N` 个
  - **1 个**：单文件归一化模式
  - **2 个及以上**：多文件合并模式
- 输出文件使用 `-o` 或 `--output` 指定（必填）

### 示例

```bash
# 单文件归一化
python merge_dbc.py A.dbc -o A_normalized.dbc

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

> 提示：单文件归一化模式下也会强制覆盖 `NmAsr*` 系列属性与 `DBName`，**不要**直接用同一个文件名作为输入和输出，建议输出到新文件以便对比。


## 参数说明

- `inputs`：输入 DBC 文件路径列表（至少 1 个）
- `-o, --output`：输出 DBC 文件路径（必填）
- `-h, --help`：查看帮助


## 工作模式

### 单文件归一化模式（输入数 = 1）

对单个 DBC 执行规整化重写，等价于"自己和自己合并一次"，会做：

- 报文按 `BO_` ID 数值升序重排
- `BU_:` 节点列表按字母升序重排（去重）
- 同一报文内同名 `SG_` 信号去重（保留首次）
- `CM_ / BA_DEF_ / BA_DEF_DEF_ / BA_ / VAL_` 完全相同的整行去重
- 注入 / 覆盖 `NmAsr*` + `NodeLayerModules` 等工程要求属性
- `DBName` 改写为输出文件名
- 按 `GB2312` 编码统一写出（失败回退 `GBK`）

### 多文件合并模式（输入数 ≥ 2）

在归一化的基础上，跨文件做并集与同 ID 信号合并。


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

5. **额外属性注入 / 覆盖**
   - `NmAsrBaseAddress`（范围由 `NM_` 报文 ID 高位段动态推断，找不到时回退 `0x4xx`）
   - `NmAsrCanMsgCycleOffset`、`NmAsrCanMsgCycleTime`、`NmAsrCanMsgReducedTime`
   - `NmAsrMessageCount`、`NmAsrNodeIdentifier`
   - `NmAsrRepeatMessageTime`、`NmAsrTimeoutTime`、`NmAsrWaitBusSleepTime`
   - `NodeLayerModules`
   - 同名属性会先被剔除再重新追加，达到"覆盖"效果

6. **节点级 `NmAsrNodeIdentifier` 注入**
   - 遍历所有 `NM_` 开头报文，按 `node_id = msg_id & 0xFF` 计算节点 ID
   - "报文属于哪个节点" 的判定：**`BO_` 行发送者优先，`NM_<NodeName>` 命名解析兜底**
   - 节点必须出现在 `BU_:` 列表中才会被采纳
   - 报文 ID 段必须与全局 `NmAsrBaseAddress` 段一致（如 `0x4xx`），否则告警跳过
   - 同节点多 NM 报文 / 不同节点 `node_id` 冲突 / 占位发送者 `Vector__XXX` 等异常都会打印告警
   - 没有 NM 报文的节点保持全局默认值 `255`，不写 `BA_` 行
   - 已存在的 `BA_ "NmAsrNodeIdentifier" BU_ <node> ...;` 会先剔除再重新写入，达到"覆盖"效果

7. **`DBName` 覆盖**
   - 删除所有原 `BA_ "DBName" "...";`
   - 追加一条以输出文件名（去除 `.dbc` 后缀）为值的赋值


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

- 当前模式（单文件归一化 / 多文件合并）
- 输入文件数量及路径
- 输出文件路径
- `NmAsrBaseAddress` 推断结果
- `NmAsrNodeIdentifier` 各节点注入结果
- `DBName` 覆盖结果
- 合并统计信息（消息、注释、属性定义、值表数量、注入额外属性条数）


## 常见问题

1. **提示"至少需要提供1个输入DBC文件"**
   - 请确认命令中传入了至少一个输入文件

2. **提示"文件不存在"**
   - 请检查输入路径是否正确，建议使用绝对路径

3. **终端显示乱码**
   - Windows 终端可能显示编码不一致，但不代表输出文件损坏
   - 可在 DBC 工具中直接验证中文显示是否正常

4. **单文件归一化后属性被改写**
   - 这是预期行为：脚本会强制注入 / 覆盖 `NmAsr*` 与 `NodeLayerModules`，并把 `DBName` 改写为输出文件名
   - 如需保留原始内容用于对比，请将输出指向不同的文件名
