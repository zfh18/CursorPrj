# SERES PDX Generator

本目录用于将 SERES 诊断调查表 Excel 生成 CANdelaStudio 15 可导入的 ODX/PDX 包。

当前脚本：

```text
pdxGen_SERES.py
cddGen_SERES.py
```

当前模板：

```text
templates\SERES_ECU_CAN_v15.pdx
templates\SERES_ECU_CAN_v15.cdd
```

当前输入示例：

```text
SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx
```

生成结果：

```text
output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.pdx
output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.cdd
```

更详细的 Excel 解析规则见：

```text
SERES_诊断调查表解析指南.md
```

## 环境要求

需要 Python 3，并安装以下 Python 包：

```powershell
python -m pip install openpyxl lxml odxtools
```

脚本还依赖同级项目中的 VOYAN 基础生成器：

```text
..\VOYAN\pdxGen_VOYAN.py
```

脚本启动时会按以下路径查找：

```text
..\VOYAN\pdxGen_VOYAN.py
.\pdxGen_VOYAN.py
```

CANdela 验证环境：

```text
Vector CANdelaStudio 15
ODX Import 15.x
```

## 目录结构

推荐目录结构：

```text
SERES\
  pdxGen_SERES.py
  cddGen_SERES.py
  SERES_诊断调查表解析指南.md
  README.md
  SERES_诊断调查表_*.xlsx
  templates\
    SERES_ECU_CAN_v15.pdx
    SERES_ECU_CAN_v15.cdd
  output\
    <生成的 PDX / CANdela 导出的 CDD>
..\VOYAN\
  pdxGen_VOYAN.py
```

注意：

```text
不要把 CANdela 导入后另存的 .cdd 当作模板 PDX 使用
默认模板 PDX 必须存在于 templates\SERES_ECU_CAN_v15.pdx
默认模板 CDD 必须存在于 templates\SERES_ECU_CAN_v15.cdd
```

## 快速开始

在 `SERES` 目录下执行：

```powershell
python .\pdxGen_SERES.py
```

脚本会自动选择当前目录下第一个非临时 `.xlsx` 文件，生成：

```text
output\<Excel 文件名>.pdx
```

当前样例成功输出类似：

```text
Generated: output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.pdx
Parsed: 23 DID identifiers, 69 DID data objects, 46 converted DID data objects, 3 IO DIDs, 8 routines, 57 DTCs, 5 snapshot DIDs, 2 snapshot records, 2 extended records
```

## 命令行参数

完整用法：

```powershell
python .\pdxGen_SERES.py [输入Excel] [--template 模板PDX] [--output-dir 输出目录] [--no-validate]
```

参数说明：

```text
输入Excel        可选。不指定时，自动选当前目录第一个非 ~$ 开头的 .xlsx
--template       可选。默认 templates\SERES_ECU_CAN_v15.pdx
--output-dir     可选。默认 output
--no-validate    可选。跳过 odxtools 校验
```

指定输入文件：

```powershell
python .\pdxGen_SERES.py ".\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx"
```

指定模板和输出目录：

```powershell
python .\pdxGen_SERES.py `
  ".\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx" `
  --template ".\templates\SERES_ECU_CAN_v15.pdx" `
  --output-dir ".\output"
```

跳过 `odxtools` 校验：

```powershell
python .\pdxGen_SERES.py --no-validate
```

仅在排查 `odxtools` 安装问题时使用 `--no-validate`。正常交付前不要跳过校验。

## 生成 CDD

`cddGen_SERES.py` 会先调用 `pdxGen_SERES.py` 生成 PDX，再调用 CANdelaStudio 命令行导入模板 CDD，生成目标 CDD。

默认用法：

```powershell
python .\cddGen_SERES.py ".\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx"
```

缺省参数：

```text
PDX 生成脚本: pdxGen_SERES.py
PDX 模板:     templates\SERES_ECU_CAN_v15.pdx
CDD 模板:     templates\SERES_ECU_CAN_v15.cdd
输出目录:     output
输出 PDX:     output\<Excel 文件名>.pdx
输出 CDD:     output\<Excel 文件名>.cdd
导入日志:     output\<Excel 文件名>.candela-import.log
```

指定 CDD 模板、输出 CDD 和 CANdelaStudio 路径：

```powershell
python .\cddGen_SERES.py `
  ".\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx" `
  --cdd-template ".\templates\SERES_ECU_CAN_v15.cdd" `
  --cdd-output ".\output\SERES_零重力主驾_v15.cdd" `
  --candela-exe "C:\Program Files\Vector CANdelaStudio 15\Bin\CANdelaStudio.exe"
```

目标 CDD 属于自动生成产物。如果输出路径已存在，脚本会默认覆盖原文件。需要保留多个版本时，用 `--cdd-output` 指定不同文件名。

CANdelaStudio 自动查找顺序：

```text
1. --candela-exe
2. 环境变量 CANDELA_STUDIO_EXE
3. 注册表 HKLM\SOFTWARE\Vector\CANdelaStudio
4. C:\Program Files\Vector CANdelaStudio *\Bin\CANdelaStudio.exe
```

脚本会优先根据 `templates\SERES_ECU_CAN_v15.cdd` 头部的 `CANDELA/@dtdvers` 选择同主版本 CANdelaStudio，例如 `15.0.4` 会优先选择 CANdelaStudio 15.x。

## 本地验证

语法检查：

```powershell
python -m py_compile .\pdxGen_SERES.py
python -m py_compile .\cddGen_SERES.py
```

生成 PDX：

```powershell
python .\pdxGen_SERES.py
```

odxtools 校验：

```powershell
python -m odxtools list ".\output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.pdx" --all
```

如果只想看是否通过，可以把输出重定向：

```powershell
python -m odxtools list ".\output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.pdx" --all > $null
```

辅助检查 PDX 内容：

```powershell
python C:\Users\Fenghua\.codex\skills\diagnostic-odx-pdx\scripts\pdx_inspect.py `
  ".\output\SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.pdx" `
  --contains TesterPresent_Send `
  --contains ControlDTCSetting_On `
  --contains ControlDTCSetting_Off `
  --contains ENVDATA_ALLDTCS `
  --contains STR_Snapshot_Ventilation_status
```

## CANdelaStudio 验证流程

推荐每次改脚本后都按以下顺序验证：

1. 运行 `python -m py_compile .\pdxGen_SERES.py`。
2. 运行 `python .\pdxGen_SERES.py` 重新生成 PDX。
3. 运行 `odxtools list --all`。
4. 在 CANdelaStudio 15 中打开模板 CDD 或新建导入流程。
5. 导入 `output\<Excel 文件名>.pdx`。
6. 观察导入日志中是否有 `E:` fatal error。
7. 保存为 `.cdd`。
8. 关闭 CANdelaStudio。
9. 重新打开刚保存的 `.cdd`。
10. 等待 consistency check 完成。
11. 确认没有 fatal inconsistency。

只通过 `odxtools` 不代表一定能通过 CANdela。CANdela 对以下内容更敏感：

```text
DIAG-SERVICE 子节点顺序
CANdelaServiceInformation SDG
flat DID 服务激活信息
CDD reopen 后的 qualifier 唯一性
Snapshot/ExtendedData 的结构写法
DOP/STRUCTURE 短名长度
```

## 生成逻辑摘要

脚本解析 Excel 后生成以下内容：

```text
CoverInfo: ECU 名称、CAN ID、通信参数、session timing
DID: ReadDataByIdentifier / WriteDataByIdentifier flat services
IO DID: InputOutputControlByIdentifier flat services
Routine: RoutineControl flat services
DTC: DTC-DOP RecordDataType 和 DTC 文本表
Snapshot: ENVDATA_ALLDTCS、snapshot record number DOP
ExtendedData: extended record number DOP 和 mux cases
Core services: session/reset/tester present/DTC setting 等基础服务及 NoResponse 配对
```

Snapshot/ExtendedData 的 record 显示名来自源表，不默认泛化：

```text
Snapshot record name: 优先使用 3_2 表第 3 列 Snapshot Record Num 的原始文本，例如 1（首次故障）、2（最近故障）
ExtendedData record name: 优先使用第 4 列英文描述和第 5 列中文描述，例如 Failure counter / 故障发生计数器
只有源表单元格和可用表头都没有名称时，才 fallback 为 Snapshot Record 0xNN 或 Extended Data Record 0xNN
这些名称会写入 record number DOP，并同步用于 ExtendedData MUX case
```

IO DID 只应包含 0x2F InputOutputControl 相关服务：

```text
ReturnControl
Reset
Freeze
Control
```

默认不包含 `Read` 服务。`templates\SERES_ECU_CAN_v15.cdd` 中的 IO Control 类模板也应保持无 `Read`，否则导入后再导入 CANoe 时 IO Control ID 会多出不需要的 Read。

当前模板使用 flat service 方案，不使用 VOYAN 的 table-based DID 服务。也就是说，每个 DID 会生成独立服务，例如：

```text
<DID_SHORT_NAME>_Read
<DID_SHORT_NAME>_Write
```

每个服务通过 `CANdelaServiceInformation` SDG 提供 CANdela 所需实例信息，其中 DID 服务会带：

```text
DiagInstanceStaticValue = DID 十进制值
DiagInstanceQualifier = DID short name
ServiceQualifier = Read / Write
```

## 当前样例的期望数量

用当前 Excel 生成时，控制台应输出：

```text
23 DID identifiers
69 DID data objects
46 converted DID data objects
3 IO DIDs
8 routines
57 DTCs
5 snapshot DIDs
2 snapshot records
2 extended records
```

说明：

```text
"23 DID identifiers" 是唯一 DID 数量
"69 DID data objects" 是 DID 子数据对象数量
表内序号最大值为 68，但有重复序号，不等于 DID 数量
```

## 常见问题

### FileNotFoundError: templates\SERES_ECU_CAN_v15.pdx

原因：

```text
模板 PDX 不存在或被移动
```

处理：

```text
确认 templates\SERES_ECU_CAN_v15.pdx 已恢复
或通过 --template 指定正确模板
```

### Cannot find the reusable VOYAN writer

原因：

```text
脚本找不到 ..\VOYAN\pdxGen_VOYAN.py
```

处理：

```text
确认 SERES 与 VOYAN 目录是同级
或把 pdxGen_VOYAN.py 放到 SERES 目录
```

### odxtools validation failed

处理顺序：

```text
1. 先看错误文件和行号
2. 解压 output PDX，定位 SERES_ECU_CAN_v15.odx-d
3. 检查引用 ID-REF 是否存在
4. 检查 DIAG-SERVICE、STRUCTURE、DOP 等 XML 子节点顺序
5. 修复脚本后重新生成，不要手改 output PDX
```

### CANdela 导入时报 PRE-CONDITION-STATE-REFS

典型日志：

```text
element 'PRE-CONDITION-STATE-REFS' is not allowed for content model
```

原因：

```text
DIAG-SERVICE 子节点顺序不符合 ODX 2.2.0
PRE-CONDITION-STATE-REFS 必须在 STATE-TRANSITION-REFS 前面
```

脚本中已有 `validate_diag_service_child_order()` 防止再次生成此类错误。

### CANdela 重新打开 CDD 报 Bitfield 重名

典型日志：

```text
Namespace 'Data objects of DID': Non-unique qualifier found (Bitfield. Path:
qpath:/Base_Variant/[DID]Ventilation_status/Bitfield
```

原因：

```text
Snapshot 位域子信号被平铺进 ENVDATA_ALLDTCS，CANdela reopen 时拆出多个同名 Bitfield
```

当前修复：

```text
ENVDATA_ALLDTCS 中每个 Snapshot DID 使用：
PHYS-CONST: DID 号
VALUE: 引用 Snapshot STRUCTURE 的整体数据参数
```

### NoResponse 服务被 CANdela skip

典型日志：

```text
Skipped ... already covered by second DIAG-SERVICE using SupPosRespMsgIndBit
```

通常可接受。CANdela 会把 `NoResponse` 和带肯定响应的基础服务合并理解。重点检查不带 `_NoResponse` 的基础服务是否已导入，例如：

```text
TesterPresent_Send
ControlDTCSetting_On
ControlDTCSetting_Off
```

### COMPARAM warning 很多

常见低风险 warning：

```text
CP_CanFuncReqFormat unsupported string
CP_CanPhysReqExtAddr unmapped
CP_CanRespUSDTExtAddr unmapped
CP_ECULayerShortName unmapped
```

只要这些核心参数导入成功，通常不影响当前 CAN 通信配置：

```text
ReqCanId = 0x705
ResCanId = 0x785
ReqCanIdFunc = 0x7DF
UudtResCanId = 0xFFFFFFFF
Baudrate = 500000
P2/P2*/S3/STmin/BS
```

说明：

```text
ReqCanIdFunc 是功能请求 ID，仍按调查表/模板配置为 0x7DF。
UudtResCanId 是 CANoe 中的 "UUDT from ECU"，默认禁用为 0xFFFFFFFF。
```

## 重新适配新调查表的建议流程

1. 复制新 Excel 到 SERES 目录。
2. 确认没有打开 Excel 造成 `~$*.xlsx` 锁文件影响判断。
3. 运行 `python .\pdxGen_SERES.py ".\新文件.xlsx"`。
4. 对比控制台数量和 Excel 肉眼预期。
5. 如果数量异常，先看 `SERES_诊断调查表解析指南.md` 中的 sheet 起始行和列位。
6. 如果 sheet 名或列位变化，优先只改解析函数，不改 ODX 写入函数。
7. 重新运行全部本地验证。
8. CANdela 导入、保存、重新打开。

## 修改脚本时的原则

推荐保持这条边界：

```text
parse_* 函数只负责 Excel -> SurveyData
update_* 函数只负责 SurveyData -> ODX/PDX
```

不要在 ODX 写入阶段直接读取 Excel，也不要在 Excel 解析阶段写 XML。这样后续换模板或换表头时，问题边界会清楚很多。

优先保留模板架构：

```text
协议层、COMPARAM-SPEC、基础服务、DTC/Snapshot/ExtendedData 模板结构尽量复用
只替换调查表驱动的数据内容
```

生成后不要手改 output PDX；所有修复应落到 `pdxGen_SERES.py`，再重新生成。
