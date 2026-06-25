# VF PDX/CDD 生成项目

本目录是 VF 诊断调查表到 CANdelaStudio 15 CDD 的自包含生成流程。

## 文件说明

- `pdxGen_VF.py`: 读取 VF 诊断调查表 `.xlsx`，生成 CANdela/ODX 兼容的 `.pdx`。自包含，内置 ODX 写入基础层，运行时不依赖其它脚本。
- `cddGen_VF.py`: 先调用 `pdxGen_VF.py` 生成 PDX，再调用 CANdelaStudio CLI 导入到 CDD 模板。
- `templates/VF_ECU_CAN_v15.pdx`: PDX/ODX 结构模板。
- `templates/VF_ECU_CAN_v15.cdd`: CANdelaStudio 15 CDD 导入模板。
- `output/`: 默认输出目录，可重复生成并覆盖。

## 快速使用

生成 PDX:

```powershell
python .\pdxGen_VF.py .\VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx
```

生成 CDD:

```powershell
python .\cddGen_VF.py .\VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx
```

生成物默认路径:

```text
output/VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.pdx
output/VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.cdd
output/VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.candela-import.log
```

## 常用参数

指定模板和输出目录:

```powershell
python .\pdxGen_VF.py .\input.xlsx --template .\templates\VF_ECU_CAN_v15.pdx --output-dir .\output
```

跳过 `odxtools` 校验:

```powershell
python .\pdxGen_VF.py .\input.xlsx --no-validate
```

指定 CANdelaStudio:

```powershell
python .\cddGen_VF.py .\input.xlsx --candela-exe "C:\Program Files\Vector CANdelaStudio 15\Bin\CANdelaStudio.exe"
```

指定 CDD 输出:

```powershell
python .\cddGen_VF.py .\input.xlsx --cdd-output .\output\VF_target.cdd
```

## 当前基线

当前输入文件 `VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx` 的解析基线:

- 48 个 DID 标识。
- 220 个 DID 数据对象。
- 118 个非 identity 转换的数据对象。
- 2 个 IO Control DID。
- 15 个 Routine 子服务实例。
- 58 个 DTC。
- 9 个 Snapshot DID。
- 3 个 Snapshot record 编号，包括 `0x01`、`0x02`、`0xFF/All`。
- 2 个 Extended Data record。

## 验证命令

语法检查:

```powershell
python -m py_compile .\pdxGen_VF.py .\cddGen_VF.py
```

查看帮助:

```powershell
python .\pdxGen_VF.py --help
python .\cddGen_VF.py --help
```

生成并执行 `odxtools` 校验:

```powershell
python .\pdxGen_VF.py .\VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx
```

PDX 烟测:

```powershell
python C:\Users\Fenghua\.codex\skills\diagnostic-odx-pdx\scripts\pdx_inspect.py `
  .\output\VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.pdx `
  --contains ENVDATA_ALLDTCS `
  --contains DTCSnapshotRecordData `
  --contains FaultMemory_Read_DTC_snapshot_record_by_DTC_number `
  --contains FaultMemory_Read_DTC_extended_data_record_by_DTC_number `
  --contains DTC_911716 `
  --contains Driver_motor_control_Control `
  --contains Driver_motor_control_ReturnControl `
  --contains Passenger_motor_control_Control `
  --contains Passenger_motor_control_ReturnControl `
  --contains eraseMemory_Start
```

生成 CDD 并解析 CANdela 导入日志:

```powershell
python .\cddGen_VF.py .\VF89NP_SCM_ODX_EOL_AS_Merged_V1.3.1.xlsx
```

## CANdela 导入结果

当前 CANdelaStudio 版本:

```text
C:\Program Files\Vector CANdelaStudio 15\Bin\CANdelaStudio.exe
15.0.01100
```

最近一次验证结果:

- `Imported 81 DiagInstance(s) with 100 CANdela Service(s) into 'Base_Variant'`
- 非 `_NoResponse` 的 `Skipped ODX DIAG-SERVICE`: 0

当前成功导入的关键服务:

- `FaultMemory_Read_DTC_snapshot_record_by_DTC_number`
- `FaultMemory_Read_DTC_extended_data_record_by_DTC_number`
- `Driver_motor_control_Control`
- `Driver_motor_control_ReturnControl`
- `Passenger_motor_control_Control`
- `Passenger_motor_control_ReturnControl`
- `eraseMemory_Start`
- `Vehicle_Identification_Number_Read`
- `CodingSession_Start`
- `ProgrammingSession_Start_NoResponse` 被 CANdela 按 SPRMIB 合并到 `ProgrammingSession_Start`
- `EnableRxAndDisableTx_Control`
- `RequestSeedOfSecurityLevelFBL_Request`
- `SendKeyOfSecurityLevelFBL_Send`

当前保留的已知警告:

- `_NoResponse` 服务被 CANdela 合并到带 `SupPosRespMsgIndBit` 的基础服务，这是可接受提示。
- `Warning: DTC table in Diagnostic Instance qpath:/Base_Variant/FaultMemory' has no DTC.` 当前日志同时显示 58 个 DTC 被创建，输出 CDD 中也能检索到 `DTC_0X911716` 和 DTC 文本；该警告按模板初始 FaultMemory 表提示处理，但交付前仍建议在 CANdelaStudio 中打开 CDD 手动确认 DTC collection。
- 部分 COMPARAM 默认值或帧格式字符串无法映射到 CANdela 字段。核心 CAN ID、波特率和定时参数已导入时，此类提示通常为低风险。

## 重要兼容处理

- VF 模板没有共享 flat-service 写入器所需的 `z_7_Read`、`z_Read`、`z_Control`、`z_ReturnControl` 占位服务，生成器会临时补内存占位，再生成平铺 DID/IO/Routine 服务，最后移除占位。
- VF 模板原始 `TextTable_DTC` 是数值 DOP，CANdela ExtendedData 表映射要求 DTC TextTable；生成器会把它规范成 `TEXTTABLE` 并填充 58 个 DTC key。
- ExtendedData record number 的显示名来自 `Extended Data` 页 A 列 `Data name`，例如 `Fault occurrence counter 01`、`Aging counter 02`，不会再简单拼成 `Extended Data Record 0x01`。
- Snapshot 0x19 04 必须使用 CANdela 认可的 `ENV-DATA-DESC -> ENV-DATA` 形状。VF 模板原本没有 `ENV-DATAS`，生成器会补 `ENVDATA_ALLDTCS` 和 `DTCSnapshotRecordData`，否则 CANdela 会跳过 Snapshot 服务。
- IOControl 的 `ReturnControl` 请求不能携带 `ControlOptionRecord`，否则 CANdela 会把同一 DID 下的 `Control` 服务分析出来但不落到 CDD；生成器会对非 `0x03 Control` 请求移除该参数。
- `Diagnostics Services` 页的固定核心子功能会同步到 PDX：`0x10 0x41/0xC1` Coding Session、`0x10 0x82` Programming suppress、`0x28 0x01/0x81` EnableRxAndDisableTx、`0x27 0x07/0x08` FBL SecurityAccess。`0x27 0x05/0x06` 在调查表中为 `U`，生成器会从输出服务中移除。
- `templates/VF_ECU_CAN_v15.cdd` 的 `Subfunction_SecurityAccess` 已正式补齐 `0x07/0x08`，用于 CANdela 导入 `0x27` FBL SecurityAccess；`cddGen_VF.py` 直接使用该模板，不再创建临时 CDD 模板副本。
- `type=identical` 转换文本按 identity 处理，避免把 `addressAndLengthFormatIdentifier` 等字段误解析成重叠枚举刻度。
- `type=BCD` / `DataType=BCD` 按 packed BCD 数值处理，生成 `A_UINT32` + `BASE-TYPE-ENCODING="BCD-P"`，避免误生成 `TEXTTABLE` 和固定文本 `BCD`。
- `type=texttable` 仅作为转换类型声明，不参与枚举刻度；例如 `0xF186` 的 `Active Diagnostic Session` 不会再生成伪枚举 `0x0E=texttable`。
- `phy=XX*0.01` / `phy=raw*0.01` / `type=ax+b` 按线性浮点转换处理，生成 `A_FLOAT64`；未显式填写 `precision` 时从系数/偏移小数位推导，例如 `0.01` 生成 `PRECISION=2`。

当前 BCD 导入验证:

- PDX 中 `BASE-TYPE-ENCODING="BCD-P"` 数量为 50，`<VT>BCD</VT>` 数量为 0。
- CDD 中 `enc='bcd'` 数量为 100，`>BCD<` 文本文本映射数量为 0。
- `0xF102` 的 `ECU Calibration Number Byte#0..#3` 在 CDD 中导入为 `IDENT`，`CVALUETYPE/PVALUETYPE enc='bcd' df='dec'`。

当前线性浮点导入验证:

- `0xFD0B` 的 `The first power supply voltage` / `The Second power supply voltage` 生成 `A_FLOAT64` + `PRECISION=2`。
- CDD 中对应 `PVALUETYPE bl='64' enc='dbl' df='flt' sig='2'`，转换系数保持 `COMP f='0.01' o='0'`。

## 已知未覆盖范围

- `Diagnostics Services` 页中 Bootloader 下载链路 `0x34 RequestDownload`、`0x36 TransferData`、`0x37 RequestTransferExit` 当前未生成到 PDX/CDD。它们需要完整 Flash/Download 协议建模，不属于简单子功能克隆；如果目标 CDD 必须包含 Bootloader 刷写链路，需要作为下一步单独适配。

## 交付前建议

1. 用上面的命令重新生成 PDX 和 CDD。
2. 打开 `output/*.candela-import.log`，确认没有非 `_NoResponse` 的 `Skipped ODX DIAG-SERVICE`。
3. 在 CANdelaStudio 15 中打开生成的 `.cdd`，等待一致性检查完成。
4. 手动抽查 DID、DTC、Snapshot、ExtendedData、IOControl 和 Routine 服务。
5. 如果要导入 CANoe，额外确认物理请求 ID、功能请求 ID、响应 ID、波特率、P2/P2*、S3、STmin、BlockSize。
