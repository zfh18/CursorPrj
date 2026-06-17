# VOYAH 诊断调查表 Excel 解析指南

本文档描述 VOYAH（岚图）主机厂诊断调查表 Excel 的结构，供从头解析该文件时参考。

---

## 文件概览

调查表包含以下 Sheet：

| Sheet 名称 | 用途 |
|-----------|------|
| `0_1_Cover` | ECU 基本信息、CAN ID |
| `0_2_RevisionManagement` | 版本修订记录 |
| `1_0_CAN(FD)...` | CAN(FD) 刷写关键参数要求 |
| `1_1_ApplicationServices` | 应用层诊断服务（默认会话和扩展会话） |
| `1_2_ApplicationServices(OS)` | 应用层诊断服务（含 OS 模式）**→ 嵌入式 ECU 不使用此页** |
| `1_3_BootService` | Bootloader 诊断服务（编程会话） |
| `2_Communication Contorl Type` | 通信控制类型（0x28）的子功能支持 |
| `3_1_DTC Information` | DTC 故障码列表 |
| `3_2_Snapshot&Extended Data List` | 快照 DID 和扩展数据记录 |
| `4_1_Read&Write DID` | **读写 DID 定义（核心）** |
| `4_2_IO DID` | **输入输出控制 DID** |
| `4_3_Routine DID` | **例程控制 DID** |
| `5_Terms` | 术语定义 |
| `6_OIL` | 开放问题清单 |
| `7_负响应码` | NRC 负响应码列表 |

---

## 一、`0_1_Cover` — ECU 基本信息

### 提取数据

| 数据 | 位置 | 示例 |
|------|------|------|
| ECU 名称 | 第 11-12 行，B 列 | `SCU_RL` |
| 车型 | 第 9 行，E 列 | `H66` |
| ECU 发送 ID（响应） | 第 12 行，C 列 | `ECU Tx:0x786` |
| ECU 接收 ID（物理寻址） | 第 13 行，C 列 | `ECU Rx (Phy):0x706` |
| ECU 接收 ID（功能寻址） | 第 14 行，C 列 | `ECU Rx (Fun):0x7DF` |
| 供应商名称 | 第 12 行，E 列 | 武汉…公司 |

### 说明

- CAN ID 格式为 `ECU Tx:0x786`，十六进制值在 `0x` 之后
- 第一列（A 列）通常为空
- 网络类型（CAN(FD)）在第 11 行 D 列

---

## 二、`4_1_Read&Write DID` — 读写 DID 定义

### 列结构

表头在第 9-10 行（序号/DID 号/描述/大小/字节/位/数据内容…），但实际列位置不因表头文字而异，以下是各列的固定含义：

| 列 | 含义 | 示例值 |
|----|------|--------|
| A | 空（无数据） | |
| B | 序号 | `1`, `2`, `14` |
| C | **DID 编号**（十六进制） | `F087`, `0x0D80` |
| D | **DID 描述**（中英文，换行分隔） | `vehicleManufacturerSparePartNumber` |
| E | **数据总字节数** | `12`, `16`, `1` |
| F | **参数字节范围** | `0-11`, `2-3`, `1`, 空 |
| G | **参数位范围** | `0-95`, `0-15`, `0`, `7` |
| H | **参数名称**（中英文） | `VehicleManufacturerSparePartNumber` |
| I | 范围最小值 | `0`, 空 |
| J | 范围最大值 | `65535`, `24`, 空 |
| K | **单位** | `V`, `-`, `km/h` |
| L | **换算/枚举/示例** | 见下方详解 |
| M | **数据类型** | `ASCII`, `Hex(Unsigned)` |
| N | **写安全等级** | `N`, `Level1`, `LevelFBL` |
| O | 应用会话 0x01 访问权限 | `R`, `R/W`, `N` |
| P | 应用会话 0x03 访问权限 | `R`, `R/W`, `N` |
| Q | Boot 会话 0x01 访问权限 | `R`, `R/W`, `N` |
| R | Boot 会话 0x02 访问权限 | `R`, `R/W`, `N` |
| S | Boot 会话 0x03 访问权限 | `R`, `R/W`, `N` |
| T+ | 备注/其他 | |

### DID 行与参数行的识别

**DID 首行**的特征：
- C 列包含有效的十六进制数（如 `F087`、`F18C`、`0x0D80`）
- 标准 UDS DID（0xF000 系列）通常**不带** `0x` 前缀
- 自定义 DID（0x0D80 系列）通常**带** `0x` 前缀
- 首行也可能同时包含第一个参数的数据（F/G/H 列非空）

**参数子行**的特征：
- B、C、D 列均为空
- F、G、H 列有值（字节/位/参数名）

**非数据行的特征**（应跳过）：
- B 列包含 `These DIDs are`、`Please add your own`、`Please select` 等说明文字
- 整行仅 A 列或全空

### 字节(B)和位(G)的解析规则

#### 字节列（F 列）

| 原始值 | 含义 | bytepos（起始字节） |
|--------|------|---------------------|
| `0-1` | 字节 0 到 1 | 0 |
| `2-3` | 字节 2 到 3 | 2 |
| `6-11` | 字节 6 到 11 | 6 |
| `1` | 字节 1 | 1 |
| 空 | 继承上一个参数的结束位置 | 0（首参数默认） |

只取 `-` 前面的数字作为起始字节。

#### 位列（G 列）

| 原始值 | 含义 | bitpos | bitlen |
|--------|------|--------|--------|
| `0-15` | 位 0 到 15 | 0 | 16 |
| `0-7` | 位 0 到 7 | 0 | 8 |
| `0-47` | 位 0 到 47 | 0 | 48 |
| `0` | 仅位 0 | 0 | **1** |
| `1` | 仅位 1 | 1 | **1** |

关键规则：
- 带 `-` 的：bitlen = 第二个数 - 第一个数 + 1
- **单个数字不带 `-` 的：表示单个 bit 位，bitlen = 1**（不是 8！）
- 只有 `0-7` 这种明确的 8 位范围，bitlen 才是 8

### 数据类型（M 列）

| 值 | 含义 | CDD 对应 |
|----|------|---------|
| `ASCII` | ASCII 字符串，每个字节一个字符 | 文本类型，编码=ASCII，显示格式=Text |
| `Hex(Unsigned)` | 无符号十六进制数值 | 数值类型，编码=Unsigned，显示格式=Hex |

### 读写权限（N 列）

| 值 | 含义 |
|----|------|
| `N` | 只读，不需要安全解锁 |
| `Level1` | 可写，需要 Security Level 1 解锁 |
| `LevelFBL` | 可写，需要 FBL 安全等级解锁 |

### 会话支持（O-S 列）

每个会话列的值：

| 值 | 含义 |
|----|------|
| `R` | 该会话下支持读取 |
| `R/W` | 该会话下支持读写 |
| `N` | 该会话下不支持 |

应用会话 = 0x01（默认）/ 0x03（扩展），Boot 会话 = 0x01/0x02/0x03（编程）。

### 换算列（L 列）的三种格式

L 列（Conversion）包含三种截然不同的数据类型，需要区分：

#### 类型一：枚举值

格式：
```
0x0: Invalid;
0x1: Valid;
```

**识别特征**：包含 `0x` 开头的十六进制值，后跟 `:` 和文字标签。多个条目用 `;` 或换行分隔。

支持范围枚举：
```
0x6-0xF: 主机厂预留;
```

代表值 6 到 15（0xF）共用同一标签。

#### 类型二：换算公式

格式：
```
EX：y=ax+b
EX：a=0.1
EX：b=0
EX：precision=1
```

**识别特征**：包含 `y=ax+b`（或 `y = ax + b`）。

每个参数含义：
- `a`：斜率（浮点数）。物理值 = a × 原始值 + b
- `b`：偏移量（浮点数）
- `precision`：显示小数位数（整数）。如 precision=1，原始值 120 → 显示 12.0

示例：
- a=0.1, b=0, precision=1：原始值 120 → 显示 12.0 V
- a=1, b=0, precision=0：原始值直接显示

#### 类型三：格式示例

格式：
```
EX："MN1234567890"（数据左对齐，未使用的Byte填充空格0x20）
```

**识别特征**：以 `EX：` 或 `EX:` 开头，但**不含** `y=ax+b`。这是字符串格式示例，不需要生成类型定义。

其他示例格式包括：
```
EX：0x0A表示2010年
EX：V1.0
EX：H56A3601800AA
```

---

## 三、`4_2_IO DID` — IO 控制 DID

### 列结构

表头在第 12-13 行。

| 列 | 含义 | 示例 |
|----|------|------|
| A | 空 | |
| B | **DID 编号**（十六进制，无 `0x`） | `3D80` |
| C | 命令描述 | `Motor control` |
| D | **IO 控制参数** | `0x03` |
| E | 数据总字节数 | `2` |
| F | 参数字节 | 空、`1` |
| G | 参数位 | `0-1`、`2-3`、`4-7` |
| H | 参数名称 | `Slide rail motor driver` |
| L | 换算/枚举 | `0x0: Stop; 0x1: Horizontal forward; …` |
| M | 数据类型 | `Hex(Unsigned)` |

### IO 控制参数（D 列）含义

| 值 | 对应的 UDS 控制选项 |
|----|-------------------|
| `0x00` | ReturnControlToECU — 返回 ECU 控制 |
| `0x01` | ResetToDefault — 重置为默认值 |
| `0x02` | FreezeCurrentState — 冻结当前状态 |
| `0x03` | ShortTermAdjustment — 短期调整 |

**关键规则**：仅当调查表明确列出了某个控制参数值，才表示该 IO DID 支持对应的控制操作。未列出的控制参数不应包含在 CDD 中。

### 多参数 DID 结构

同一个 IO DID 首行以下的行（B/C 列为空）为参数子行，与 4_1 Sheet 的模式相同。参数按字节位置排列。

IO DID 通常不包含 Read 服务——只有控制服务。数据解析按 byte/bit 展开，支持枚举。

---

## 四、`4_3_Routine DID` — 例程控制 DID

### 列结构

表头在第 11-12 行。

| 列 | 含义 | 示例 |
|----|------|------|
| A | 空 | |
| B | **RID 编号**（十六进制） | `0x0202`, `0x6D80` |
| C | 例程描述 | `CheckProgrammingIntegrity` |
| D | **控制类型** | `0x01 StartRoutine` / `0x02 StopRoutine` / `0x03 RequestRoutineResults` |
| E | **是否支持** | `Y` / `N` |
| F | **请求参数定义**（结构化） | 见下方 |
| G | **响应状态枚举** | 见下方 |
| H | 安全等级 | `Level1`, `LevelFBL`, `N` |
| I | 应用会话 0x01 | `Y`, `N` |
| J | 应用会话 0x03 | `Y`, `N` |
| K-O | 其他会话 | `Y`, `N` |

### RID 行与子功能行的识别

**首行**（B 列有十六进制 RID）定义了该例程的名称、安全等级、会话支持、以及 StartRoutine 的请求参数和响应状态。

**子功能行**（B 列为空，D 列有值）定义了 StopRoutine / RequestRoutineResults 的支持情况（E 列 Y/N）。

**注意**：首行的 D 列也是 `0x01 StartRoutine`——这是第一个子功能。不要遗漏首行的子功能信息。

### 请求参数（F 列）的解析

F 列（RoutineControlOption）是多参数结构化文本。每个参数以 `Name:` 开头：

```
Name:dataAdress,
Byte:0-3,
Bit:0-31;

Name:dataLength,
Byte:4-7,
Bit:0-31;

Name:dataChecksum,
Byte:8-11,
Bit:0-31;
```

解析方法：
1. 以 `Name:` 为分隔符切分
2. 每个分段中提取 `Byte:` 后的起始字节、`Bit:` 后的位范围
3. 如果有 `Conversion:` 则提取枚举值

也有的例程参数为 `N/A`（无参数）或单参数格式。

### 响应状态（G 列）的解析

G 列（RoutineStatus）是单参数结构化文本：

```
Name:Status,
Byte:0,
Bit:0-7,
Conversion:
0x00:校验通过
0x01:未通过校验;
```

解析方法：提取 Name/Byte/Bit/Conversion，与 4_1 Sheet 的换算列规则相同。

---

## 五、`3_1_DTC Information` — DTC 故障码

### DTC 数据列

表头在第 11 行。数据从第 12 行开始。

| 列 | 含义 | 示例 |
|----|------|------|
| A | 序号 | `1`, `11` |
| B | **DTC 显示码**（7 位 SAE 格式） | `B1E0031` |
| C | **DTC 字节码**（6 位 UDS 3 字节格式） | `9E0031` |
| D | 故障含义（中英文） | `Hall signal fault of the left slide motor` |
| E | 优先级 | `1`, `2`, `3` |

### DTC 编码说明

调查表提供两种编码：

**显示码（B 列）**：7 位 SAE 格式
- 第 1 位是类别字母：`P`(Powertrain)、`C`(Chassis)、`B`(Body)、`U`(Network)
- 后 6 位十六进制编码故障信息

**字节码（C 列）**：6 位 UDS 3 字节格式
- 直接对应 CDD 中的 DTC 值
- 转换公式：取 C 列的十六进制值即为 UDS DTC 数值

**DTC Status 定义**在第 67-75 行（属于另一段数据）。

---

## 六、`3_2_Snapshot&Extended Data List`

### 快照 DID（上半部分）

表头在第 10 行。

| 列 | 含义 | 示例 |
|----|------|------|
| B | 记录序号 | `1` |
| C | Snapshot Record Num | `0x01` |
| D | **快照 DID 编号** | `0x0B00`, `0x0B01` |
| E | 快照记录描述 | `Ignition Switch Signal` |

快照 DID（`0x0B00`-`0x0B0A`）是通用车辆 DID（点火信号、电池电压、里程、车速等），为 DTC 快照记录提供环境数据。这些 DID 通常不需要 DIAGINST，只需在 DIDS 中定义并在快照段中引用。

### 扩展数据（下半部分）

表头在第 29 行。

| 列 | 含义 | 示例 |
|----|------|------|
| B | 序号 | `1` |
| C | Extended Data Record Num | `1` |
| D | 扩展数据描述 | `Fault number` |
| E | 数据字节数 | `3` |

子行（B/C 列为空）包含该记录的各个子字段（Fault Ocurrence Counter、Fault Aged Counter 等）。

---

## 七、`1_1_ApplicationServices` 等 — 诊断服务列表

### 通用服务列表格式

三个服务 Sheet（`1_1`、`1_2(OS)`、`1_3_Boot`）结构相同：

| 列 | 含义 | 示例 |
|----|------|------|
| B | **Service ID（SID）** | `0x10`, `0x22`, `0x27`, `0x34` |
| C | 服务名称 | `DiagnosticSessionControl` |
| D | ECU 是否支持 | `Y` / `N` |
| E | 禁止正响应位(SPRMB) | `Y` / `N` |
| F | **子功能** | `0x01 DefaultSession` |
| G | 子功能是否支持 | `Y` / `N` |
| H-J | 会话模式支持 | `Y` / `N` |
| K | 寻址方式 | `P`(物理) / `F`(功能) / `P/F`(两者) |
| L | 安全等级 | `N`, `Level1`, `LevelFBL` |
| M | 支持的负响应码 | `12,13,22` |

### 子功能行的识别

服务首行：B 列有 SID（如 `0x10`），F 列可能已经有第一个子功能。
子功能行：B 列为空，F 列有子功能定义。

### 三个 Session Sheet 的区别

| Sheet | 覆盖会话 | 用途 | 适用场景 |
|-------|---------|------|---------|
| `1_1_ApplicationServices` | 0x01(默认), 0x03(扩展) | 应用层诊断 | 所有 ECU |
| `1_2_ApplicationServices(OS)` | 0x01, 0x02(编程), 0x03 | 应用+OS 完整覆盖 | 带 OS 的 ECU，**嵌入式 ECU 不使用** |
| `1_3_BootService` | 0x01, 0x02, 0x03 | Bootloader | 所有 ECU |

嵌入式 ECU（如 SCU_RL）的诊断服务定义分布在 `1_1`（应用会话）和 `1_3`（Boot 会话）两个 Sheet 中，`1_2(OS)` 页面的内容与本 ECU 无关，解析时应跳过。

---

## 通用注意事项

### Excel 单元格值

- 所有单元格值应以文本形式读取
- 空单元格为 `None`
- 数字单元格（如 size=12）可能被 Excel 存储为数值
- 部分单元格值带单引号前缀（Excel 文本格式标志）
- 多行文本用 `\n` 分隔（如中文/英文双语名称）

### Header 行定位

不要硬编码行号（不同版本可能偏移）。通过扫描前 20 行的关键字定位表头：

- DID Sheet：C 列包含 `DID Num`
- IO DID Sheet：B 列包含 `DID Number`
- Routine Sheet：B 列包含 `Routin DID` 或 D 列包含 `RoutineControlType`
- DTC Sheet：B 列包含 `DTC Display`

### 数据范围

数据从 header 行下一行开始，直到遇到下一个说明行（如 `Please select if…`）或空行。部分 Sheet 在数据之后还有 Status 定义或其他子表。

### 多 Sheet 合并

部分调查表将 DID 分为两个 Sheet（如 `System DID` 和 `ECU DID`）。需要解析两个 Sheet 后合并为统一的 DID 列表。

### 编码

文件包含简体和繁体中文字符。读取和写入时始终使用 UTF-8 编码。
