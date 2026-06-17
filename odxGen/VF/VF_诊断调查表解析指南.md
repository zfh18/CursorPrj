# VF 诊断调查表解析指南

本文档记录 `pdxGen_VF.py` 对 `VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx` 的解析规则和 CANdela 兼容策略。

## 工作簿结构

当前识别的核心 sheet:

- `Change Log & General Info`
- `Diagnostics Services`
- `System DID`
- `ECU DID`
- `DTC-List`
- `Snapshot DIDs`
- `Extended Data`
- `Routines Data (0x31)`
- `IO Control (2F)`

流程类、说明类 sheet 当前不参与 PDX 生成。

## Cover 与通信参数

来源 sheet:

- `Change Log & General Info`

当前解析值:

- ECU name: `SCMF`
- Vehicle: `VF89NP`
- Supplier: `innosensing`
- Baudrate: `500kbps`
- Functional request ID: `0x6FF`
- Physical request ID: `0x69E`
- Physical response ID: `0x61E`
- Tester address: `0x9E`
- ECU address: `0x1E`
- Functional target address: `0xFF`

生成器会把波特率转换成 `500000`，并更新 ODX 的 CAN/ISO-TP COMPARAM。

## DID 解析

来源 sheet:

- `System DID`
- `ECU DID`

`System DID` 解析规则:

- 表头行: 第 2 行。
- 数据起始行: 第 3 行。
- A 列: DID Number。
- B 列: DID Name。
- C 列: RWState。
- D 列: Parameter。
- E 列: BytePos。
- F 列: BitPos。
- G 列: BitLength。
- H 列: DataType。
- I 列: MethodType。
- J 列: Unit。
- K 列: Application session。
- L 列: Boot Loader session。
- M 列: Security Level。
- N 列: Requirement。
- O 列: Supported。
- 仅生成 `Supported = Yes` 的 System DID。

`ECU DID` 解析规则:

- 表头结构基本同 `System DID`。
- 没有独立 supported flag 时，表内列出的 DID 默认视为支持。

DID 生成策略:

- DID request 使用 `0x22 + DID`。
- 可写 DID 使用 `0x2E + DID`。
- 结构参数按 BytePos、BitPos、BitLength 生成。
- `type=identical` 不再生成枚举转换，按 identity 处理。
- 枚举转换、线性转换会生成相应 DOP。

## DTC 解析

来源 sheet:

- `DTC-List`

解析规则:

- 表头行: 第 2 行。
- 数据起始行: 第 3 行。
- DTC 编号示例: `0xB111716`、`0xU110087`。
- 支持 OBD 类前缀 `P`、`C`、`B`、`U` 到 24-bit UDS trouble code 的编码转换。

编码示例:

- 输入显示码 `B111716`。
- 生成 UDS trouble code `0x911716`。
- CDD 显示码保留 `B111716`。

当前基线:

- 58 个 DTC。
- `DTC_911716` 文本为 `ECU power supply voltage too low`。

DTC 兼容策略:

- VF PDX 模板原始没有 `DTC-DOPS` 容器时，生成器会创建 `DTC-DOP RecordDataType`。
- `TextTable_DTC` 会规范成 CANdela ExtendedData 可识别的 `TEXTTABLE`，并写入 DTC key。
- ExtendedData 的 DTC 到 RecordNumber 映射使用 `TABLE DTCExtendedDataRecordNumber`。

## DID BCD 解析

来源字段:

- `System DID` / `ECU DID` 的 `DataType`、`MethodType`。

解析规则:

- `MethodType=type=BCD` 或 `DataType=BCD` 表示 packed BCD 编码的无符号数值，不是枚举文本。
- 生成器输出 `COMPU-METHOD CATEGORY=IDENTICAL`、`DIAG-CODED-TYPE BASE-DATA-TYPE=A_UINT32 BASE-TYPE-ENCODING=BCD-P`、`PHYSICAL-TYPE A_UINT32`。
- 例如 `0xF102` 的 `ECU Calibration Number Byte#0..#3` 不再生成 `TEXTTABLE` / `<VT>BCD</VT>`。
- `type=texttable` / `type=identical` 等类型声明行不参与枚举刻度解析；只有后续 `0x..=...` 或 `0x..:...` 数据行会进入 `TEXTTABLE`。
- `phy=XX*0.01`、`phy=raw*0.01`、`type=ax+b` 等线性算式生成 `LINEAR` 浮点 DOP，物理类型为 `A_FLOAT64`。
- 未显式填写 `precision` 时，生成器从线性系数/偏移的小数位推导显示精度，例如 `0.01` 推导为 `PRECISION=2`。

CANdela 已验证结果:

- `0xF102` 的 `ECU Calibration Number Byte#0..#3` 导入为 `IDENT`。
- CDD 中对应 `CVALUETYPE/PVALUETYPE` 为 `enc='bcd' df='dec'`。
- `0xFD0B` 的两个 power supply voltage 参数导入为 `LINCOMP`，`PVALUETYPE bl='64' enc='dbl' df='flt' sig='2'`，`COMP f='0.01' o='0'`。

## Snapshot 解析

来源 sheet:

- `Snapshot DIDs`

解析规则:

- 数据起始行: 第 5 行。
- 支持标记列: K 列。
- 第 3 行标题中解析 snapshot record 编号。
- 当前识别 record: `0x01`、`0x02`，同时保留 `0xFF/All` 语义。
- 当前支持 Snapshot DID 数量: 9。

Snapshot 生成策略:

- 每个 Snapshot DID 生成一个内部 `STRUCTURE`，用于保留 DID 后的数据对象定义。
- CANdela 0x19 04 导入不接受直接把 DID 常量和结构展开在 `ListOfDTCSnapshotRecord` 中。
- 生成器会补 `ENV-DATAS/ENVDATA_ALLDTCS`，其中每个 Snapshot DID 用 `PHYS-CONST DID + VALUE data structure` 表达。
- 生成器会补 `ENV-DATA-DESCS/DTCSnapshotRecordData`，并让 `ListOfDTCSnapshotRecord` 引用该 ENV-DATA-DESC。
- `DTCSnapshotRecordNumbers_All_except_FF` 会规范为 8-bit `TEXTTABLE`，供请求参数和正响应记录号使用。

CANdela 已验证结果:

- `FaultMemory_Read_DTC_snapshot_record_by_DTC_number` 成功导入。
- 导入日志显示该服务 created 1 InterService。

## Extended Data 解析

来源 sheet:

- `Extended Data`

解析规则:

- 数据起始行: 第 6 行。
- Record 显示名来源: A 列 `Data name`，例如 `Fault occurrence counter 01`、`Aging counter 02`。
- 支持标记列: H 列。
- 当前支持 record: `0x01`、`0x02`。

ExtendedData 生成策略:

- 每个 Extended Data record 生成对应结构。
- `DTCExtendedDataRecordNumbers_All` 和 `DTCExtendedDataRecordNumbers_All_except_FF` 会规范为 8-bit `TEXTTABLE`，文本来自 A 列 `Data name`。
- `DTCExtendedDataRecordData` MUX 的 `CASE` 使用数值型 `LOWER-LIMIT/UPPER-LIMIT`，与 record number 保持一致。
- 0x19 06 请求使用 `TABLE-KEY DTC + TABLE-STRUCT DTCExtendedDataRecordNumber`，满足 CANdela 对 DTC 到 ExtendedData record 映射的要求。

CANdela 已验证结果:

- `FaultMemory_Read_DTC_extended_data_record_by_DTC_number` 成功导入。
- 导入日志显示该服务 created 1 InterService。

## Routine 解析

来源 sheet:

- `Routines Data (0x31)`

解析规则:

- 表头行: 第 2 行。
- 数据起始行: 第 3 行。
- A 列: Session。
- B 列: ControlType。
- C 列: RID。
- D 列: RID Name。
- E 列: Req/Resp。
- F 列: Parameter。
- G 列: BytePos。
- H 列: BitPos。
- I 列: BitLength。
- J 列: DataType。
- K 列: MethodType。
- L 列: Unit。
- M 列: Security。
- O 列: Supported。

生成策略:

- `StartRoutine` 生成 `_Start` 服务。
- `StopRoutine` 生成 `_Stop` 服务。
- `RequestRoutineResults` 生成 `_RequestResults` 服务。
- OptionRecord 和 StatusRecord 分别生成结构。

当前基线:

- 15 个 Routine 子服务实例。
- `eraseMemory_Start` 已成功导入 CANdela。

## IO Control 解析

来源 sheet:

- `IO Control (2F)`

解析规则:

- 主要数据从第 24 行开始。
- A 列: IOControlParam。
- B 列: DID。
- C 列: DID Name。
- D 列: Req/Resp。
- E 列: Parameter。
- F 列: BytePos。
- G 列: BitPos。
- H 列: BitLength。
- I 列: DataType。
- J 列: MethodType。
- K 列: Unit。
- L 列: Security。

当前基线:

- 2 个 IO DID。
- `Driver_motor_control_Control` 已成功导入 CDD。
- `Driver_motor_control_ReturnControl` 已成功导入 CDD。
- `Passenger_motor_control_Control` 已成功导入 CDD。
- `Passenger_motor_control_ReturnControl` 已成功导入 CDD。

IOControl 兼容策略:

- `0x03 shortTermAdjustment` 请求携带 `ControlOptionRecord`。
- `0x00 returnControlToECU` 请求不携带 `ControlOptionRecord`，否则 CANdela 会分析出 `Control` 服务但最终只导入 `ReturnControl`。
- 正响应保留 `ControlStatusRecord`，用于承载反馈状态。

## PDX 模板适配

VF PDX 模板的特点:

- 保留 CAN 相关文件和 `VF_ECU_CAN_v15.odx-d`。
- 没有共享 flat-service 写入器所需的 `z_7_Read`、`z_Read`、`z_Control`、`z_ReturnControl` 占位服务。
- 没有 `ENV-DATAS`、`ENV-DATA-DESCS`，但 Snapshot 导入需要这些容器。
- 没有原生 `DTC-DOPS` 时需要生成 `RecordDataType` DTC-DOP。

适配策略:

- 生成器在内存中临时创建 flat service 占位服务，再复用本地 ODX 写入基础层生成 DID/IO/Routine flat services。
- 生成完成后移除占位服务。
- 对 Snapshot、ExtendedData、DTC TextTable 做 VF 专用兼容修正。
- `Diagnostics Services` 页的固定核心子功能会参与生成：`0x10 0x41/0xC1` Coding Session、`0x10 0x82` Programming suppress、`0x28 0x01/0x81` EnableRxAndDisableTx、`0x27 0x07/0x08` FBL SecurityAccess。
- 调查表中 `0x27 0x05/0x06` 为 `U`，生成器会移除模板中对应的 Level5 SecurityAccess 服务，避免 CDD 中保留未支持实例。
- `templates/VF_ECU_CAN_v15.cdd` 的 `Subfunction_SecurityAccess` 已正式补齐 `0x07/0x08`，用于 CANdela 导入 `0x27` FBL SecurityAccess；`cddGen_VF.py` 直接使用正式模板，不再创建临时模板副本。
- 保持模板通信协议架构，不替换 ISO-TP/CAN 协议文件。

## 当前未覆盖范围

- `Diagnostics Services` 页中 `0x34 RequestDownload`、`0x36 TransferData`、`0x37 RequestTransferExit` 标记为 Bootloader Programming 支持，但当前 PDX/CDD 生成器未建模这条下载传输链路。
- 这三项需要完整 Flash/Download 协议、数据格式、地址长度格式、block sequence、transfer parameter record 等结构，不应按普通子功能服务直接克隆。若交付范围要求 Bootloader 刷写服务，需要单独适配和 CANdela 验证。

## 当前已知警告

CANdela 导入日志中保留:

- `_NoResponse` 服务被合并到基础服务，这是 CANdela 对 SPRMIB 的正常处理。
- `DTC table in Diagnostic Instance qpath:/Base_Variant/FaultMemory' has no DTC.` 当前同时可见 DTC collection 创建日志和 CDD 中的 DTC 文本，按模板初始表提示处理。
- 若出现非 `_NoResponse` 的 `Skipped ODX DIAG-SERVICE`，应视为高风险并优先修复。

## 回归关注点

修改解析或模板适配后重点确认:

- PDX 能通过 `odxtools`。
- CANdela 导入日志没有非 `_NoResponse` skipped service。
- `Diagnostics Services` 固定服务审计除 `0x34/0x36/0x37` 外没有缺口。
- `FaultMemory_Read_DTC_snapshot_record_by_DTC_number` 仍成功导入。
- `FaultMemory_Read_DTC_extended_data_record_by_DTC_number` 仍成功导入。
- `eraseMemory_Start` 不再出现 `overlapping COMPU-SCALES`。
- DTC `0x911716`、`0xD10087` 等 OBD 类编码仍正确。
- Snapshot record number DOP 保持 8-bit TextTable。
- ExtendedData record number DOP 保持 8-bit TextTable，显示名来自 `Extended Data` 页 A 列 `Data name`。
- ExtendedData `TABLE-ROW/KEY` 与 `TextTable_DTC` 的物理值保持一致。
