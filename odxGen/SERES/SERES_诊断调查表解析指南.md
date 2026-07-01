# SERES 诊断调查表解析指南

本文档记录 SERES 诊断调查表解析为 ODX/PDX 时的关键规则，方便后续从零适配同主机厂的新调查表。当前实现脚本为 `pdxGen_SERES.py`，输入示例为：

```text
SERES_诊断调查表_G19项目EVR_G19项目EV_零重力主驾座椅控制器_V1.3-20260420.xlsx
```

当前脚本的总体思路是：

```text
SERES Excel -> parse_seres_survey() -> SurveyData -> update_odx_seres() -> SERES_ECU_CAN_v15.pdx
```

SERES 表格结构与 VOYAH 项目接近，因此脚本复用了 `..\VOYAH\pdxGen_VOYAH.py` 中的通用数据模型、DOP/STRUCTURE 生成器、单位处理、DTC 文本表等基础能力；SERES 自己负责 Excel schema 解析和 CANdela v15 模板的差异化写入。

## 文件角色

核心文件：

```text
pdxGen_SERES.py
templates\SERES_ECU_CAN_v15.pdx
templates\SERES_ECU_CAN_v15.cdd
..\VOYAH\pdxGen_VOYAH.py
```

生成文件：

```text
output\<输入 Excel 文件名>.pdx
```

CANdela 导入后通常会另存为 `.cdd`，例如：

```text
output\SERES_零重力主驾_v15.cdd
```

## Workbook Sheet 总览

当前工作簿包含以下主要 sheet：

```text
0_1_Cover
GeneralInfo
0_2_RevisionManagement
1_1_ApplicationServices
1_2_BootService
2_Communication Contorl Type
3_1_DTC list
3_2_Snapshot&Extended Data List
4_1_DID of read&write
Coding
4_2_IO DID
4_3_Routine DID
Flash
DataBlock
5_Terms
6_OIL
Predefined
```

当前脚本实际解析的 sheet：

```text
GeneralInfo
0_1_Cover
1_1_ApplicationServices
1_2_BootService
3_1_DTC list
3_2_Snapshot&Extended Data List
4_1_DID of read&write
4_2_IO DID
4_3_Routine DID
Predefined
```

当前脚本暂不解析或只间接受影响的 sheet：

```text
0_2_RevisionManagement
2_Communication Contorl Type
Coding
Flash
DataBlock
5_Terms
6_OIL
```

## 通用解析规则

空值处理：

```text
"", "/", "N/A", "NA", "NONE", "NULL" 视为空
```

结束标记：

```text
单元格文本以 "#" 开头时，认为该数据块结束，例如 #endofdata
```

Demo 数据：

```text
行号、DID 描述或命令描述中出现 demo/DEMO 时跳过
```

中英文名称：

```text
英文列作为 SHORT-NAME 来源
中文列用于 LONG-NAME，格式通常为 "English / 中文"
只有中文或只有英文时，使用非空值
```

十六进制：

```text
支持 0x705、705、CF00、0x10 DefaultSession 等形式
DID/RID 限制为 0x0000..0xFFFF
服务 ID 限制为 0x00..0xFF
```

Byte/Bit：

```text
Byte 支持 0、0-1、0~1、ALL
Bit 支持 0、0-7、0~7、ALL
Byte 为空时默认 0
Bit 为空或 ALL 时按 Byte 范围推导长度
```

换算：

```text
优先同时解析英文换算列和中文换算列
选择优先级：枚举 enum > 线性 linear > identity
支持 0x00: Invalid; 0x01: Valid 这类枚举
支持 phy=XX*0.1、y=x*0.1+1 这类线性换算
超过 32 bit 的枚举会降级为 identity，避免 CANdela 生成异常表
```

短名：

```text
所有 SHORT-NAME 会做 CANdela 可接受的清洗
DOP 和 STRUCTURE 最终限制到 64 字符以内，超长时加稳定 hash 后缀
同一容器内重复短名会加序号或 hash，避免 CANdela reopen 报命名冲突
```

## GeneralInfo 和 Cover

优先从 `GeneralInfo` 获取基础信息：

```text
ECU-Name
Supplier ID
Protocol
CAN Channel
CAN Baudrate
CAN Functional Request ID
CAN Physical Request ID
CAN Response ID
P2 / P2* / S3
APP STmin(ECU)
BS(ECU)
N_As / N_Ar / N_Bs / N_Cr
```

`0_1_Cover` 作为补充来源：

```text
B11: ECU 名称
C16: CAN Response ID
C17: CAN Physical Request ID
C18: CAN Functional Request ID
```

当前样例解析结果：

```text
ECU Name: DSM
Physical Request ID: 0x705
Response ID: 0x785
Functional Request ID: 0x7DF
Baudrate: 500000
```

时间单位规则：

```text
GeneralInfo 中未明确为 us/micro 时，按 ms 转 us 写入 ODX COMPARAM
P2/P2Ex 写入 session state 描述时使用 ms
```

## 1_1 / 1_2 服务矩阵

`1_1_ApplicationServices` 从第 7 行开始解析：

```text
2: Service ID
3: Diagnostic Service Name English
5: 服务是否支持
6: Sub-function English
8: 子功能是否支持
10: Default session
11: Extended session
13: Security Access
```

`1_2_BootService` 从第 10 行开始解析：

```text
2: Service ID
3: Diagnostic Service Name English
5: 服务是否支持
6: Sub-function English
8: 子功能是否支持
10: Default session
11: Programming session
12: Extended session
14: Security Level
```

解析结果用于核心基础服务的前置条件。对 `1_2_BootService` 中模板缺失但明确支持的 SecurityAccess 子功能，还会增量生成平铺服务。脚本目前维护这些服务的 session/security：

```text
DiagnosticSessionControl: 0x10 01/03
ECUReset: 0x11 01
ClearDiagnosticInformation: 0x14
ReadDTCInformation: 0x19
SecurityAccess: 0x27
CommunicationControl: 0x28 00/03
TesterPresent: 0x3E
InputOutputControlByIdentifier: 0x2F
RoutineControl: 0x31
ControlDTCSetting: 0x85 01/02
```

BootService 中的 SecurityAccess 特殊规则：

```text
如果 1_2_BootService 支持 0x27 0x09 RequstSeedOfSecurityLevelFBL，
则生成 RequstSeedOfSecurityLevelFBL_Request。

如果 1_2_BootService 支持 0x27 0x0A SendKeyOfSecurityLevelFBL，
则生成 SendKeyOfSecurityLevelFBL_Send。

0x09/0x0A 使用 BootService 的 Programming session。
SendKeyOfSecurityLevelFBL_Send 会补齐 SecurityAccess 状态迁移 Locked_Unlocked_FBL。
```

注意：

```text
NoResponse 服务和带肯定响应的基础服务需要成对存在
CANdela 可能跳过 NoResponse，因为它会识别 SPRMB 覆盖关系，这是可接受现象
但基础响应服务本身必须存在，否则模板里的核心服务可能保持未激活
```

## 4_1 DID of read&write

数据起始行：

```text
第 12 行
```

关键列：

```text
2: Num / 序号
3: DID Num / DID号
4: DID Description English
5: DID Description Chinese
6: Size(Bytes)
7: Byte
8: Bit
9: Sub Data Name English
10: Sub Data Name Chinese
11: Data Type
12: Conversion English
13: Conversion Chinese
14: Range Min
15: Range Max
16: Unit
19: $22 APP Default session 0x01
20: $22 APP Extended session 0x03
21: $22 Boot Default session 0x01
22: $22 Boot Programming session 0x02
23: $22 Boot Extended session 0x03
25: $2E APP Default session 0x01
26: $2E APP Extended session 0x03
27: $2E Boot Default session 0x01
28: $2E Boot Programming session 0x02
29: $2E Boot Extended session 0x03
```

解析策略：

```text
按 DID 聚合，重复 DID 行合并为同一个 DidDef
每一行子数据生成一个 ParamDef
$22 列决定 Read 服务可用 session
$2E 列决定 Write 服务可用 session
写安全等级从 $2E 访问列中取第一个非 N 值
```

当前样例容易误解的一点：

```text
表内有 23 个唯一 DID 号
有 69 行 DID 子数据对象
其中序号最大值为 68，但序号 18 重复，所以不是 68 个 DID
CANdela 树上应看到 23 个 DID 实例，子数据在 DID 结构内部
```

## 4_2 IO DID

数据起始行：

```text
第 10 行
```

关键列：

```text
2: DID Number
3: Command Description English
4: Command Description Chinese
5: InputOutputControlParameter
6: ControlState size
7: Byte
8: Bit
9: Sub Data Name English
10: Sub Data Name Chinese
11: Data Type
12: Conversion English
13: Conversion Chinese
14: Range Min
15: Range Max
16: Unit
```

解析策略：

```text
按 DID 聚合
同一 DID 的多个 InputOutputControlParameter 合并到 controls 集合
当前支持 0x00 ReturnControl、0x01 Reset、0x02 Freeze、0x03 Control
size <= 0 的行只记录 control，不生成子数据
```

CANdela/CANoe 兼容要点：

```text
IO Control ID 默认不应包含 Read 服务。
CDD 模板中的 IO Control 类只保留 ReturnControl、Reset、Freeze、Control。
如果模板类中带 Read，CANdela 导入 PDX 后可能给每个 IO DID 自动带出 Read，导入 CANoe 后会多出不需要的 IOControl Read。
```

## 4_3 Routine DID

数据起始行：

```text
第 11 行
```

关键列：

```text
2: RoutineDID
3: DID Description English
4: DID Description Chinese
5: RoutineControlType
6: Subfunction supported
7: Routine Control Option Size
8: Option Byte
9: Option Bit
10: Option Sub Data Name
11: Option Data Type
12: Option Conversion
13: Option Range Min
14: Option Range Max
15: Option Unit
16: Routine Status Size
17: Status Byte
18: Status Bit
19: Status Sub Data Name
20: Status Data Type
21: Status Conversion
22: Status Range Min
23: Status Range Max
24: Status Unit
25: Security Level
26: APP Default session
27: APP Extended session
28: Boot Default session
29: Boot Programming session
30: Boot Extended session
```

解析策略：

```text
按 RID 聚合
按 RoutineControlType 拆 subfunction
只支持 0x01 StartRoutine、0x02 StopRoutine、0x03 RequestResults
第 6 列为 Y 时认为子功能支持
Option Size > 0 时生成 RoutineControlOptionRecord
Status Size > 0 时生成 RoutineStatusRecord
```

## 3_1 DTC list

数据起始行：

```text
第 8 行
```

关键列：

```text
4: DTC Display，例如 U010187
5: DTC Bytes，例如 C10187
6: DTC Meaning English
7: DTC Meaning Chinese
13: Service Level
```

解析策略：

```text
DTC Display 必须匹配 [PCBU][0-9A-F]{6}
DTC Bytes 必须是 6 位十六进制
Service Level 中提取数字作为 DTC priority
写入模板的 RecordDataType DTC-DOP
同步更新 DTC 文本表
为每个 DTC 生成扩展数据记录默认 table row
```

当前样例解析到：

```text
57 DTCs
```

## 3_2 Snapshot & Extended Data

Snapshot 数据起始行：

```text
第 8 行
```

Snapshot 关键列：

```text
3: Snapshot Record Num
4: Data Identifier
5: Snapshot Record Description English
6: Snapshot Record Description Chinese
7: Size(Bytes)
8: Byte
9: Bit
10: Sub Data Name English
11: Sub Data Name Chinese
12: Data Type
13: Conversion English
14: Conversion Chinese
15: Range Min
16: Range Max
17: Unit
18: Remarks
```

Snapshot record 命名规则：

```text
record number 的显示名必须优先来自第 3 列 Snapshot Record Num 的原始文本。
例如源表中的 "1（首次故障）"、"2（最近故障）" 要原样写入 snapshot record number DOP。
只有第 3 列只有纯数字/纯 hex 且没有业务名称时，才允许使用表头 "Snapshot Record Num / 快照记录号" 加记录号作为名称来源。
源表单元格和表头都没有可用名称时，才 fallback 为 "Snapshot Record 0xNN"。
```

Extended Data 区域定位：

```text
扫描第 3 列，找到包含 "Extended Data Record Num" 的行
该行之后按 Extended Data 解析
```

Extended Data 关键列：

```text
3: Extended Record Num
4: Extended Record Description English
5: Extended Record Description Chinese
6: Size(Bytes)
7: Byte
8: Bit
9: Sub Data Name
10: Data Type
11/12/16: Conversion 候选列
13: Range Min
14: Range Max
15: Unit
```

Extended Data record 命名规则：

```text
record number 的显示名必须优先来自第 4 列英文描述和第 5 列中文描述。
英文和中文都存在时使用 "English / 中文"，例如 "Failure counter / 故障发生计数器"。
只有英文或只有中文时使用非空描述。
源表确实没有英文/中文描述时，才 fallback 为 "Extended Data Record 0xNN"。
该名称必须同时写入 extended record number DOP 的 VT，以及 DTCExtendedDataRecordData MUX case 的 LOWER-LIMIT/UPPER-LIMIT。
```

Snapshot 去重：

```text
按 DID 聚合 SnapshotDef
同一 Snapshot DID 下使用 name + byte_pos + bit_pos + bit_len 去重
```

当前样例解析到：

```text
5 snapshot DIDs
2 snapshot records
2 extended records
```

当前 Snapshot DID：

```text
0xCF00 Battery Voltage
0xCF01 Vehicle Speed
0xCF03 Odometer
0xCF05 Time
0xCF07 Ventilation status
```

CANdela 兼容要点：

```text
ENVDATA_ALLDTCS 中每个 Snapshot DID 必须生成：
1. 一个 PHYS-CONST 参数表示 DID 号
2. 一个 VALUE 参数引用 Snapshot STRUCTURE

不要把 Snapshot 子信号直接平铺到 ENVDATA_ALLDTCS。
否则 Ventilation_status 这类位域快照会在 CANdela reopen 时生成多个同名 Bitfield，报：
Non-unique qualifier found (Bitfield. Path: qpath:/Base_Variant/[DID]Ventilation_status/Bitfield)
```

## ODX/PDX 写入规则

模板：

```text
templates\SERES_ECU_CAN_v15.pdx
```

保留文件：

```text
ISO_11898_2_DWCAN.odx-cs
ISO_11898_3_DWFTCAN.odx-cs
ISO_15765_2.odx-cs
ISO_15765_3.odx-cs
ISO_15765_3_on_ISO_15765_2.odx-c
SAE_J2411_SWCAN.odx-cs
SERES_ECU_CAN_v15.odx-d
index.xml
```

主要写入步骤：

```text
1. 更新 DIAG-LAYER-CONTAINER / BASE-VARIANT 长名称
2. 确保单位定义
3. 为 DID、IO DID、Routine、Snapshot、ExtendedData 生成 DOP 和 STRUCTURE
4. 生成平铺 DID Read/Write 服务
5. 生成平铺 IOControl 服务
6. 生成平铺 RoutineControl 服务
7. 删除模板占位服务 z_7_Read / z_Read / z_Control / z_ReturnControl
8. 删除 Upload_Download_RequestDownload，避免 ALFID 模板不匹配导致 CANdela 跳过
9. 写入 DTC-DOP、snapshot、extended data
10. 写入 BASE-VARIANT COMPARAM
11. 写入 session timing 描述
12. 补齐核心 NoResponse 对应的 base response 服务
13. 根据 1_2_BootService 增量生成 boot-only SecurityAccess 服务，例如 0x27/0x09、0x27/0x0A FBL
14. 更新核心服务前置条件
15. 缩短 DOP/STRUCTURE SHORT-NAME
16. 修正文档 revision label
```

平铺服务要求：

```text
SERES 模板使用 flat DID/IO/Routine 服务，不使用 VOYAH 那种 table-based DID 服务
每个 DID Read/Write 服务需要自己的 DIAG-SERVICE
服务 SDG 必须包含 CANdelaServiceInformation
DID 服务需要 DiagInstanceStaticValue = DID 十进制值
```

前置条件顺序：

```text
ODX 2.2.0 中 DIAG-SERVICE 子节点顺序必须保持：
SHORT-NAME, LONG-NAME, DESC, ADMIN-DATA, SDGS, FUNCT-CLASS-REFS,
AUDIENCE, PROTOCOL-SNREFS, RELATED-DIAG-COMM-REFS,
PRE-CONDITION-STATE-REFS, STATE-TRANSITION-REFS,
COMPARAM-REFS, REQUEST-REF, POS-RESPONSE-REFS, NEG-RESPONSE-REFS,
POS-RESPONSE-SUPPRESSABLE
```

如果 `PRE-CONDITION-STATE-REFS` 放在 `STATE-TRANSITION-REFS` 后面，CANdela 导入会直接 schema 失败。

## 当前样例解析结果

当前样例表运行结果：

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

这些数字是很有用的回归检查。后续换表后，如果数量突然大幅变化，应先检查：

```text
sheet 名称是否变化
起始行是否变化
列位置是否变化
#endofdata 是否提前出现
demo 行是否被误判
DID/RID/DTC 十六进制格式是否变化
换算列是否移动
```

## 从零适配新 SERES 表的检查清单

1. 打开 workbook，确认 sheet 名称是否仍包含当前关键字。
2. 检查每个数据区的起始行是否仍一致。
3. 检查 DID、IO、Routine、DTC、Snapshot 的列位是否仍一致。
4. 确认 GeneralInfo 中 CAN ID、P2/P2Ex/S3、N_As/N_Bs 等字段名称是否仍一致。
5. 运行脚本，记录解析数量。
6. 用 `odxtools` 验证 PDX。
7. 用 `pdx_inspect.py` 检查核心服务、DTC、snapshot 是否存在。
8. 用 CANdela 导入 PDX。
9. 保存为 CDD，关闭后重新打开。
10. 运行 CANdela consistency check，确认没有 fatal inconsistency。

## 常见 CANdela 日志解释

低风险 COMPARAM warning：

```text
CP_CanFuncReqFormat unsupported string
CP_CanPhysReqExtAddr / CP_CanRespUSDTExtAddr unmapped
CP_ECULayerShortName unmapped
```

只要以下核心通信参数成功导入，通常可接受：

```text
ReqCanId = 0x705
ResCanId = 0x785
ReqCanIdFunc = 0x7DF
UudtResCanId = 0xFFFFFFFF
Baudrate = 500000
P2/P2*/S3/STmin/BS 等时间参数
```

`ReqCanIdFunc` 和 `UudtResCanId` 不要混用：功能请求 ID 仍来自调查表，通常是 `0x7DF`；CANoe 中的 `UUDT from ECU` 默认应禁用为 `0xFFFFFFFF`。

NoResponse skipped：

```text
Skipped ... already covered by second DIAG-SERVICE using SupPosRespMsgIndBit
```

通常是 CANdela 正常合并 SPRMB 变体，不一定是错误。需要关注的是对应不带 `_NoResponse` 的基础服务是否已经导入并激活。

Schema fatal error：

```text
element 'PRE-CONDITION-STATE-REFS' is not allowed for content model
```

这是 XML 子节点顺序错误，必须修脚本。

CDD reopen inconsistency：

```text
Non-unique qualifier found (Bitfield. Path: qpath:/Base_Variant/[DID]Ventilation_status/Bitfield)
```

这是 Snapshot 环境数据平铺位域导致的 CANdela CDD 命名冲突。应让 `ENVDATA_ALLDTCS` 引用 Snapshot STRUCTURE，不要平铺子信号。
