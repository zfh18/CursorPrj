# CANoe 测试模块同步工具

根据 Excel 测试用例文件自动生成/同步 CANoe XML 测试模块和 CAPL 脚本。

## 功能

- 从 Excel 读取测试用例，生成 CANoe Test Module XML
- 自动生成 CAPL 脚本占位函数
- 支持 `--xml-only`（仅生成/同步 XML）
- 支持增量更新（已有内容保留，仅补缺）
- 动态同步变体（variants）属性
- 支持多层级 testgroup 嵌套

## 依赖

```bash
pip install openpyxl
```

## 使用方法

```powershell
# 只传入 Excel 文件（XML 和 CAN 文件与 Excel 同名）
python customrule_sync_canoe_module.py "UDS Flash Test Module.xlsx"

# 指定 XML 输出路径（CAN 文件与 XML 同名）
python customrule_sync_canoe_module.py "UDS Flash Test Module.xlsx" "Output.xml"

# 指定 XML 和 CAN 输出路径
python customrule_sync_canoe_module.py "UDS Flash Test Module.xlsx" "Output.xml" "Output.can"

# 仅生成/同步 XML（不创建/更新 CAN）
python customrule_sync_canoe_module.py "UDS Flash Test Module.xlsx" --xml-only

# 仅生成/同步 XML，并指定 XML 输出路径
python customrule_sync_canoe_module.py "UDS Flash Test Module.xlsx" "Output.xml" --xml-only
```

`--xml-only` 模式下会忽略 CAN 输出参数，不会创建、备份或更新 `.can` 文件。

## Excel 格式要求

脚本会自动查找包含 `CANoe` 关键字的 sheet，并识别以下列：

| 列名 | 说明 | 示例值 |
|------|------|--------|
| 测试类型（自动、手动） | 只处理 `Automatic` | Automatic, Manual |
| CANoe自动化测试类型 | XML 节点类型 | testmodule, testgroup, capltestfunction, capltestcase, preparation, completion |
| 自动化测试函数 | 函数/用例名称 | testModuleInit, Flash_APP_9V |
| 变体 | 适用的变体，可多个（空格或换行分隔） | variant1, variant1 variant2 |
| xml 层级 | 节点层级深度 | 0, 1, 2 |
| 用例 ID / 编号 | 测试用例标识 | TC-001 |
| 名称 / 用例名称 | 用例显示名称（无则用函数名） | 正常刷写测试 |
| 前置条件 | 测试前置条件 | 上电完成 |
| 步骤 / 测试步骤 / 操作步骤 | 测试步骤描述 | 1. 发送请求\n2. 校验响应 |
| 预期结果 / 期望结果 | 预期结果描述 | 收到 0x7E |

### 层级说明

| 层级 | 含义 |
|------|------|
| 0 | testmodule 根级别 |
| 1 | 第一层 testgroup 或 testmodule 的 preparation/completion |
| 2 | 第二层 testgroup 或第一层 testgroup 的子节点 |
| ... | 依此类推 |

### CANoe自动化测试类型

| 类型 | 说明 |
|------|------|
| testmodule | 测试模块（根节点） |
| testgroup | 测试组 |
| preparation | 前置准备 |
| completion | 后置清理 |
| capltestfunction | CAPL 测试函数 |
| capltestcase | CAPL 测试用例 |

## 示例 Excel 结构

| CANoe自动化测试类型 | 自动化测试函数 | 变体 | xml 层级 |
|---------------------|----------------|------|----------|
| testmodule | UDS Flash Test Module | | 0 |
| preparation | | | 1 |
| capltestfunction | testModuleInit | | 1 |
| testgroup | TG UDS 刷写测试 | | 1 |
| preparation | | | 2 |
| capltestfunction | Boot_Flash_Pre_1 | variant1 | 2 |
| capltestfunction | Boot_Flash_Pre_2 | variant2 | 2 |
| testgroup | TG1 正常刷写测试 | | 2 |
| capltestcase | Flash_APP_9V | variant1 | 2 |
| capltestcase | Flash_APP_12V | | 2 |
| completion | | | 2 |
| capltestfunction | Boot_Flash_Post | | 2 |
| completion | | | 1 |
| capltestfunction | testModuleEnd | | 1 |

## 输出文件

### XML 文件

符合 CANoe Test Module 1.8 规范的 XML 文件，包含：
- variants 定义
- testgroup 层级结构
- capltestfunction / capltestcase 节点
- preparation / completion 节点

### CAN 文件

CAPL 脚本文件，包含：
- 自动生成的 testfunction / testcase 占位函数
- 函数上方注释：用例 ID、名称、前置条件、步骤、预期结果（来自 Excel）
- GBK 编码（CANoe 默认）

## 注意事项

1. **增量更新**：已存在的 XML 节点不会被删除，只会更新 variants 属性
2. **变体同步**：变体列支持多个值（空格或换行分隔），XML 中输出为 `variants="variant1 variant2"`；variants 列表会根据 Excel 中实际使用的变体动态更新
3. **文件编码**：XML 使用 UTF-8，CAN 使用 GBK
4. **自动创建**：如果输出文件不存在，会自动创建

## LT_sync_canoe_module.py（LT 用例模板）

`LT_sync_canoe_module.py` 基于 `customrule_sync_canoe_module.py` 的 XML/CAN 同步能力，适配 LT 用例表头结构。

### 使用方法

```powershell
# 传入 Excel 和具体 sheet 名称（XML/CAN 默认按 Excel 名 + sheet 名生成）
python LT_sync_canoe_module.py "LT_case.xlsx" "网络层测试"

# 指定 XML 和 CAN 输出路径
python LT_sync_canoe_module.py "LT_case.xlsx" "网络层测试" "Output.xml" "Output.can"

# 仅生成/同步 XML
python LT_sync_canoe_module.py "LT_case.xlsx" "网络层测试" --xml-only
```

### LT Excel 表头映射

| LT 表头 | 用途 |
|------|------|
| 分类 | `testgroup` 名称 |
| 一级测试用例 | 用例显示名上半部分 |
| 二级测试用例 | 用例显示名下半部分 |
| 用例ID | `capltestcase` 函数名 |
| 前置条件 | 用例前置条件注释 |
| 测试步骤 | 用例步骤（用于生成 `testStep`） |
| 期望结果 | 用例预期结果（用于生成 `testStep`） |

### LT 规则说明

1. **用例名称规则**：`一级测试用例-二级测试用例`（若某一列为空则自动回退）
2. **testgroup 前后置函数**：每个 `testgroup` 自动生成 `preparation/completion`
3. **testgroup 函数命名**：取该组第一个用例函数名前 3 段（按 `_` 分隔）并追加 `_Pre` / `_Post`  
   例如：`CAN_UDS_NetworkLayer_001` → `CAN_UDS_NetworkLayer_Pre` / `CAN_UDS_NetworkLayer_Post`
4. **testmodule 固定函数**：根节点固定包含  
   - `preparation -> testModuleInit`（`name/title` 均为 `testModuleInit`）  
   - `completion -> testModuleEnd`（`name/title` 均为 `testModuleEnd`）
5. **testmodule 顺序约束**：`testModuleInit` 位于第一个 `testgroup` 前，`testModuleEnd` 位于最后一个 `testgroup` 后
