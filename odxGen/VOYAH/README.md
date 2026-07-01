# VOYAH PDX 生成脚本使用说明

本目录用于把岚图/VOYAH 诊断调查表 Excel 转换成可导入 Vector CANdelaStudio 15 的 PDX 文件。核心脚本是 `pdxGen_VOYAH.py`，它以 CANdelaStudio 导出的 `templates/VOYAH_ECU_CAN_v15.pdx` 作为结构模板，解析调查表中的 DID、IO DID、Routine、DTC、Snapshot、Extended Data、通信参数等内容，并重新打包生成同名 PDX。

## 目录结构

```text
VOYAH/
  pdxGen_VOYAH.py
  README.md
  templates/
    VOYAH_ECU_CAN_v15.pdx
  output/
    <生成的 PDX 文件>
  (嵌入式)VOYAH_H66_UDSonCAN_Diagnostic_Specification_SCU_RL_V1.2_20260330.xlsx
  VOYAH_诊断调查表解析指南.md
  QDH-YD07-04-2019 UDSonCAN诊断规范.pdf
```

重要文件说明：

| 文件/目录 | 说明 |
| --- | --- |
| `pdxGen_VOYAH.py` | PDX 生成脚本 |
| `templates/VOYAH_ECU_CAN_v15.pdx` | CANdelaStudio 导出的基础 PDX 模板，脚本会在它的基础上替换数据 |
| `output/` | 默认输出目录 |
| `*.xlsx` | 输入的岚图诊断调查表 |
| `VOYAH_诊断调查表解析指南.md` | 调查表字段和 Sheet 解析说明 |

## 环境要求

建议使用 Windows + Python 3.11 或更新版本。脚本当前在以下环境中使用过：

```text
Windows
Python 3.11
CANdelaStudio 15
```

需要安装 Python 依赖：

```powershell
pip install lxml openpyxl odxtools
```

依赖说明：

| 依赖 | 用途 |
| --- | --- |
| `openpyxl` | 读取 Excel 调查表 |
| `lxml` | 解析和修改 ODX XML |
| `odxtools` | 对生成的 PDX 做基础格式验证 |

如果当前机器有多个 Python 版本，建议先确认命令指向：

```powershell
python --version
python -m pip --version
```

## 快速开始

在本目录执行：

```powershell
python pdxGen_VOYAH.py
```

脚本会自动查找当前目录下第一个非临时的 `.xlsx` 文件，忽略 Excel 打开的临时文件，例如 `~$xxx.xlsx`。

成功后会看到类似输出：

```text
Generated: output\(嵌入式)VOYAH_H66_UDSonCAN_Diagnostic_Specification_SCU_RL_V1.2_20260330.pdx
Parsed: 24 DIDs, 1 IO DIDs, 8 routines, 52 DTCs, 3 snapshots, 1 extended records
```

生成文件名与输入 Excel 同名，只是扩展名变成 `.pdx`。

## 命令行参数

脚本支持以下参数：

```powershell
python pdxGen_VOYAH.py [xlsx] [--template TEMPLATE] [--output-dir OUTPUT_DIR] [--no-validate]
```

参数说明：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `xlsx` | 当前目录第一个非 `~$` 的 `.xlsx` | 指定输入调查表 |
| `--template` | `templates/VOYAH_ECU_CAN_v15.pdx` | 指定 PDX 模板 |
| `--output-dir` | `output` | 指定输出目录 |
| `--no-validate` | 不启用 | 跳过 `odxtools` 验证 |

示例 1：指定输入 Excel：

```powershell
python pdxGen_VOYAH.py ".\(嵌入式)VOYAH_H66_UDSonCAN_Diagnostic_Specification_SCU_RL_V1.2_20260330.xlsx"
```

示例 2：指定模板和输出目录：

```powershell
python pdxGen_VOYAH.py ".\SomeSurvey.xlsx" --template ".\templates\VOYAH_ECU_CAN_v15.pdx" --output-dir ".\output"
```

示例 3：临时跳过 odxtools 验证：

```powershell
python pdxGen_VOYAH.py ".\SomeSurvey.xlsx" --no-validate
```

通常不建议长期使用 `--no-validate`。只有在本机没有安装 `odxtools`，或需要快速排查脚本逻辑时才使用。

## 输入 Excel 要求

脚本面向岚图当前诊断调查表格式，主要解析以下 Sheet：

| Sheet | 内容 |
| --- | --- |
| `0_1_Cover` | ECU 名称、供应商、CAN ID 等封面信息 |
| `1_1_ApplicationServices` / `1_2_ApplicationServices(OS)` / `1_3_BootService` | UDS 服务支持情况、会话、安全等级、NRC |
| `2_Communication Contorl Type` | 通信控制相关信息 |
| `3_1_DTC Information` | DTC 列表 |
| `3_2_Snapshot&Extended Data List` | Snapshot DID 和 Extended Data Record |
| `4_1_Read&Write DID` | 普通读写 DID |
| `4_2_IO DID` | IOControl DID |
| `4_3_Routine DID` | RoutineControl DID |

注意事项：

- 不要把 Excel 临时文件 `~$xxx.xlsx` 当作输入。
- Snapshot DID 行如果没有 `Size / Byte / Bit / Signal Name / Data Type`，脚本会认为它没有有效数据对象，并跳过输出，避免 CANdela 报 `DID ... is invalid: no objects`。
- 当前生成器只输出 CAN 相关 ODX 文件，会从模板 PDX 中移除 DoIP、FlexRay、VIS 等不需要的文件。
- 输出内容依赖模板结构，建议不要随意替换 `templates/VOYAH_ECU_CAN_v15.pdx`，除非确认新模板仍是相同 OEM/Vector UDS 架构。

## 脚本生成内容

脚本会在模板基础上更新或处理以下内容：

| 类别 | 处理方式 |
| --- | --- |
| DID | 更新 `Identification_Read` / `Identification_Write` 表和服务实例 |
| IO DID | 按调查表中的 `InputOutputControlParameter` 更新 ReturnControl/Reset/Freeze/Control 服务；请求侧仅 Control 带 ControlOptionRecord，响应侧带 ControlStatusRecord；默认不生成 `IOControl_Read` |
| Routine | 更新 Start/Stop/RequestResults 表和服务实例 |
| DTC | 更新 DTC-DOP、DTC 文本表、DTC 属性 |
| Snapshot | 只输出有实际数据对象的 snapshot DID |
| Extended Data | 生成 Extended Data Record 结构，更新 `0x19 0x06` 所需的 DTC -> EDR 映射 |
| 通信参数 | 更新 CAN ID、波特率、P2/P2*、S3、ISO-TP 时间参数等 |
| 前置条件 | 为平铺服务补齐 `PRE-CONDITION-STATE-REFS` |
| Software Update | 移除 ODX 中的 `Software_Update_RequestDownload`，由 CDD 模板保留 mandatory 服务；保留 `Transmit` 和 `Stop` |
| PDX 包 | 只保留 CAN 所需文件，并更新 `index.xml` |

当前输出 PDX 通常只包含以下文件：

```text
FGL_UDS.odx-d
ISO_11898_2_DWCAN.odx-cs
ISO_15765_2.odx-cs
ISO_15765_3.odx-cs
ISO_15765_3_on_ISO_15765_2.odx-c
VOYAH_ECU_CAN_v15.odx-d
index.xml
```

## 生成后的验证

脚本默认会自动执行：

```powershell
python -m odxtools list "<生成的.pdx>" --all
```

如果 `odxtools` 验证失败，脚本会抛出异常并停止。常见原因包括：

- XML 结构非法
- PDX 缺文件
- ODX 引用断裂
- 依赖未安装或 Python 环境不正确

也可以手动验证：

```powershell
python -m odxtools list ".\output\<文件名>.pdx" --all
```

另外建议做一次 Python 语法检查：

```powershell
python -m py_compile pdxGen_VOYAH.py
```

## CANdelaStudio 导入建议

推荐流程：

1. 使用脚本生成 PDX。
2. 在 CANdelaStudio 15 中打开对应 CDD 模板或当前项目 CDD。
3. 执行 ODX/PDX ECU Import。
4. 选择 `output/` 下生成的 PDX。
5. 导入后检查 Output/Log。
6. 保存 CDD。
7. 关闭并重新打开 CDD，再执行一致性检查。

重点检查项：

| 检查项 | 期望 |
| --- | --- |
| DID 数量和名称 | 与调查表一致 |
| IOControl 服务 | 不应保留模板里的 stale fallback；应只生成调查表声明的 ReturnControl/Reset/Freeze/Control |
| `FaultMemory_Read_extended_data_record` | 应导入并支持 EDR 0x01 |
| DTC | 52 个 DTC 应存在 |
| EDR | 52 个 DTC 应支持 `Extended Data Record 0x01` |
| Snapshot | 只应包含有数据对象的 `0x0B01`、`0x0B03`、`0x0B04` |
| Software Update | `RequestDownload` 由模板保留，`Transmit` / `Stop` 来自 ODX |
| CAN ID | `ReqCanId`、`ResCanId`、`ReqCanIdFunc` 与调查表/封面一致 |
| Timing | P2、P2*、S3、STmin、BlockSize 等正确 |

## 已知 CANdela 日志说明

### `Software_Update_RequestDownload` skipped

历史上 CANdelaStudio 15 对 ODX 里的 `RequestDownload` 匹配较严格，会出现：

```text
Skipped ODX DIAG-SERVICE 'Software_Update_RequestDownload'
Reason: DIAG-SERVICE does not match any CANdela ProtocolService
```

当前脚本已经从 ODX 中移除 `Software_Update_RequestDownload`，让 CDD 模板里的 mandatory `RequestDownload` 保留。因此新生成的 PDX 不应再出现这条 warning。

### Snapshot DID `no objects`

如果保存并重新打开 CDD 后看到：

```text
DID "... 0x0B00" is invalid:
 no objects
```

通常表示空 Snapshot DID 被创建出来。当前脚本已过滤没有参数结构的 snapshot DID，只输出有实际数据对象的 snapshot。

### `ODX-Model: Error: unknown Doctype value 9`

旧版本输出的 PDX 在 CANdelaStudio 15 中可能出现：

```text
ODX-Model: Error: unknown Doctype value 9
```

原因是 CANdelaStudio 15 的 ODX Import 在处理 `FUNCTIONAL-GROUP FGL_UDS` 继承 `PROTOCOL CAN` 时，会把这个协议层类型落到内部未知 doctype enum，并打印 `unknown Doctype value 9`。这个错误发生在：

```text
BASE-VARIANT 'VOYAH_ECU_CAN' value-inherits from FUNCTIONAL-GROUP 'FGL_UDS'
FUNCTIONAL-GROUP 'FGL_UDS' value-inherits from PROTOCOL 'CAN'
ODX-Model: Error: unknown Doctype value 9
```

当前脚本已避免让 FunctionalGroup 直接 value-inherit Protocol：它会移除 `FGL_UDS -> CAN` 的 `PARENT-REF`，并让 `BASE-VARIANT VOYAH_ECU_CAN` 额外直接继承 `PROTOCOL CAN`。这样 BaseVariant 从 FGL 继承诊断服务，从 CAN 继承通信参数，但日志中不应再出现 `FUNCTIONAL-GROUP ... value-inherits from PROTOCOL ...`。

生成后的 `FGL_UDS.odx-d` 不应再包含：

```xml
<PARENT-REF ID-REF="CAN" xsi:type="PROTOCOL-REF"/>
```

生成后的 `VOYAH_ECU_CAN_v15.odx-d` 应包含 BaseVariant 到 CAN 的直接引用：

```xml
<PARENT-REF ID-REF="CAN" DOCREF="DLC_FGL_UDS" DOCTYPE="CONTAINER" xsi:type="PROTOCOL-REF"/>
```

如果仍看到这个 error，请先确认使用的是重新生成后的 `output/*.pdx`，不是修改前的旧 PDX。

### COMPARAM warnings

导入时可能看到：

```text
Skipping ODX COMPARAM 'CP_CanFuncReqFormat' ...
Skipping ODX COMPARAM 'CP_CanPhysReqExtAddr' ...
Skipping ODX COMPARAM 'CP_CanRespUSDTFormat' ...
Skipping ODX COMPARAM 'CP_ECULayerShortName' ...
Skipped 6 overwritten ODX COMPARAM value(s) ...
```

这些通常是 CANdela 无法映射某些 ODX 通信参数字符串、扩展寻址字段或 ECU layer 元数据。对于当前普通 11-bit CAN 寻址，`CP_CanPhysReqExtAddr`、`CP_CanRespUSDTExtAddr`、`CP_CanRespUUDTExtAddr` 的 overwritten value 为 `0`，跳过后不影响普通寻址；`CP_ECULayerShortName` 只是元数据；`CP_CanFuncReqFormat`/`CP_CanPhysReqFormat`/`CP_CanRespUSDTFormat` 对应 CANdela 15 没有可导入的独立通信参数字段。

核心 CAN ID 和 timing 参数仍应被导入。重点检查日志中以下参数是否为 `Imported ODX COMPARAM`：

```text
ReqCanId
ResCanId
ReqCanIdFunc
Baudrate
P2Client
P2ExClient
S3Client
StMin
Blocksize
TimeoutAs/Ar/Bs/Br/Cs/Cr
```

如果日志出现 `Unable to resolve Odxlink`、`BASE-VARIANT inherits from no PROTOCOL` 或核心 CAN ID/timing 没有被导入，则不是可忽略 warning，需要检查 PDX 继承结构。

## 常见问题

### 找不到 Excel 文件

报错：

```text
FileNotFoundError: No .xlsx survey file found in the current directory
```

处理：

- 确认当前目录下有 `.xlsx` 调查表。
- 确认文件名不是以 `~$` 开头的 Excel 临时文件。
- 或者显式指定输入文件：

```powershell
python pdxGen_VOYAH.py ".\YourSurvey.xlsx"
```

### 找不到模板 PDX

报错：

```text
FileNotFoundError: templates\VOYAH_ECU_CAN_v15.pdx
```

处理：

- 确认 `templates/VOYAH_ECU_CAN_v15.pdx` 存在。
- 或者使用 `--template` 指定模板路径：

```powershell
python pdxGen_VOYAH.py ".\YourSurvey.xlsx" --template ".\path\to\template.pdx"
```

### `odxtools` 不存在

报错可能类似：

```text
No module named odxtools
```

处理：

```powershell
pip install odxtools
```

如果只想临时生成 PDX，可以使用：

```powershell
python pdxGen_VOYAH.py --no-validate
```

### 输出 PDX 仍被 CANdela 报一致性错误

建议按顺序检查：

1. 是否使用了最新生成的 PDX，查看 `output/` 中文件的 `LastWriteTime`。
2. 是否导入了旧 CDD 中残留对象，必要时用干净模板重新导入。
3. CANdela 日志中是否还有 `Skipped ODX DIAG-SERVICE`。
4. 保存、关闭、重新打开后是否还有 `no objects`。
5. 用脚本拆包检查 ODX 中是否仍包含问题对象。

## 新调查表复用流程

对同厂家、同格式的新调查表：

1. 把新的 `.xlsx` 放到本目录。
2. 确认当前目录没有多个容易混淆的 `.xlsx`，或者直接在命令里指定输入文件。
3. 执行：

```powershell
python pdxGen_VOYAH.py ".\NewSurvey.xlsx"
```

4. 查看输出统计：

```text
Parsed: <DIDs> DIDs, <IO DIDs> IO DIDs, <routines> routines, <DTCs> DTCs, <snapshots> snapshots, <extended records> extended records
```

5. 导入 CANdelaStudio，并按本文的检查项验证。

如果新调查表的 Sheet 名、列名或字段含义发生变化，需要先更新 `pdxGen_VOYAH.py` 的解析逻辑，再重新生成。

## 开发和维护建议

修改脚本后建议至少执行：

```powershell
python -m py_compile pdxGen_VOYAH.py
python pdxGen_VOYAH.py
```

生成后建议拆包或导入验证以下关键点：

```text
Software_Update_RequestDownload 不在 ODX 中
Software_Update_Transmit 存在
Software_Update_Stop 存在
FaultMemory_Read_extended_data_record 存在
DTCExtendedDataRecordNumber 有 52 行
IOControl_Read 不存在，ReturnControl/Control 等服务与调查表控制参数一致，响应侧带 ControlStatusRecord
ENVDATA_ALLDTCS 不包含空 snapshot DID
```

维护时尽量保持脚本的处理顺序：

1. 解析调查表。
2. 为 DID/IO/Routine/Snapshot/EDR 生成结构。
3. 更新服务表和服务实例。
4. 更新 DTC 和 EDR 映射。
5. 做 CANdela 兼容性修正。
6. 裁剪为纯 CAN PDX。
7. 用 `odxtools` 验证。
