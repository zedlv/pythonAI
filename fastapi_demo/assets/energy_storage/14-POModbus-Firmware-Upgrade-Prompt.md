# 21000 固件升级弹窗与统一跳转

> 面向：设备主页 / 空间概览 / 设置页维护者  
> 相关代码：`POFirmwareUpgradePromptBuilder`、`POFirmwareUpgradeNavigator`  
> 真机回归：[13-POModbus-RealDevice-Regression-Checklist.md](./13-POModbus-RealDevice-Regression-Checklist.md) §3 并联盒子 / 子设备升级

---

## 1. 背景

设备连接后读取寄存器 **21000**（DTU 子设备列表），各节点 `DTUSubInfoState.bit1 == 1` 表示**需要升级**。  
用户在**设备首页**（或空间概览单机模式）首次数据就绪时，弹出 `POTextSelectedView` 列出待升级型号；点选后进入对应升级页。

该逻辑需与 **Android 双端一致**：本机优先、机型 tier 固定顺序、同类型按序号升序、只展示需升级项。

2026/6 重构前，iOS 按 `po_subInverterDTULists` 等粗分类聚合，且每类只取第一个 `bit1` 节点，与规范不符。现抽取为 Builder + Navigator 两层。

---

## 2. 架构

```text
21000 解析 → mainDataModel.DTUSubList
        ↓
POFirmwareUpgradePromptBuilder（POModbusHelper/Upgrade）
  · 筛选 bit1
  · tier 排序
  · 生成 POTextModel（textId = RouteType）
        ↓
EMainBaseViewController / SpaceOverviewUpgradeChecker
  · 弹 POTextSelectedView
  · 休眠 / 主机会话 / deferred 展示
        ↓ 用户点选
POFirmwareUpgradeNavigator（POFunctionClasses/Upgrade/BLEUpgrade）
  · push 对应升级 VC
```

| 类 | 所在 Pod | 职责 |
|----|----------|------|
| `POFirmwareUpgradePromptBuilder` | `POModbusHelper/Upgrade` | 无 UI；列表构建与排序 |
| `POFirmwareUpgradeNavigator` | `POFunctionClasses/Upgrade/BLEUpgrade` | 无 UI；统一 push 升级页 |

**边界**：Builder 不 import 业务 VC；Navigator 不弹窗、不校验休眠（由调用方处理）。

---

## 3. 数据来源与筛选

| 字段 | 含义 |
|------|------|
| `DTUSubList` | 21000 解析后的子节点数组 |
| `DTUSubID` | 机型 ID（如 3001=AT1、3000=S1） |
| `DTUSubSN` | 同类型序号，用于段内升序 |
| `DTUSubAddressBit.bit0` | 从机地址；**0 = 本机**（`PODTUModel.isMaster`） |
| `DTUSubInfoState.bit1` | **1 = 需要升级**（弹窗入选条件） |
| `masterDTU` | `EDTUModel` 计算属性，本机节点 |

### 3.1 额外门禁（与旧逻辑一致）

- **Epanel（3006）**：`energyViewType == 12` 或 `presentProtocolVersion < 2015` 时不纳入列表
- **弹窗会话**：`isSlaveModeConnect == YES` 的子设备主页不弹（`POModbusHostSessionForFirmwareUpgradeUI`）
- **单次检查**：设备主页 `didCheckVersion` 仅首包就绪后检查一次

---

## 4. 排序规则（与 Android 对齐）

仅 **`bit1 == 1`** 的节点进入列表；**每台需升级设备一行**（不再每类只取第一个）。

### 4.1 大段顺序（tier）

| tier | 说明 | 段内次序 |
|------|------|----------|
| **0** | **本机**（`masterDTU`） | — |
| **10** | 通讯盒 / 并机盒 | 固定机型序（见下表） |
| **20** | 逆变器 | `DTUSubID` 1–2999（排除已归入 10/30 的 ID）+ **30002**；按 `DTUSubSN` 升序 |
| **30** | 配件 | 固定机型序（见下表） |
| **35** | 扩展三方配件 | 3015 Shelly → 3016 EverHome → 2005 WT |
| **40** | 外置电池包 | `DTUSubID` 4000–4999；按 `DTUSubSN` 升序 |
| **50** | BMS 虚拟节点 | **30001** |
| **99** | 未归类 | 按 `DTUSubID` 兜底 |

同 tier、同 subOrder 时再比 `DTUSubSN`，最后比 `DTUSubID`。

### 4.2 tier 10 — 通讯盒 / 并机盒

| 顺序 | DTUSubID | 机型 |
|------|----------|------|
| 1 | 3001 | AT1 |
| 2 | 3002 | Combox |
| 3 | 3003 | PBOX |
| 4 | 3004 | EBOX |
| 5 | 3005 | Epad |
| 6 | 3008 | HA1 |
| 7 | 3007 | HD1 |
| 8 | 3011 | CHARGER2 |
| 9 | 3012 | Edock |

### 4.3 tier 30 — 配件

| 顺序 | DTUSubID | 机型 |
|------|----------|------|
| 1 | 3000 | S1 插座 |
| 2 | 3006 | Epanel |
| 3 | 3009 | SolarX 4K（DCDC） |
| 4 | 3010 | CHARGER1 |
| 5 | 3018 | SMeter |

### 4.4 列表行标题

优先 `equipmentName`（`DTUSubModel` + `DTUSubSN`），与设备子列表展示一致。

---

## 5. 路由类型（POFirmwareUpgradeRouteType）

写入 `POTextModel.textId`，由 `POFirmwareUpgradeNavigator` 消费。

| textId | 枚举 | 典型 DTUSubID / 判定 | 目标页面 |
|--------|------|----------------------|----------|
| 1 | MainSystem | 逆变器、通讯盒、CHARGER1 等 | 见 §5.1 |
| 2 | Socket | 3000 | 见 §5.2 |
| 3 | DCDC | 3009 | `UpgradeElementsViewController`（DCDC） |
| 4 | Panel | 3006 | `UpgradeElementsViewController`（Panel） |
| 5 | Pad | 3005 | `UpgradeElementsViewController`（Pad） |
| 6 | DCAC | 2000–2003 | `UpgradeElementsViewController`（DCAC） |
| 7 | SMeter | 3018 | `UpgradeElementsViewController`（Smeter） |
| 8 | Shelly | 3015 | `UpgradeElementsViewController`（Shelly） |
| 9 | EverHome | 3016 | `UpgradeElementsViewController`（EverHome） |
| 10 | WT | 2005 | `UpgradeElementsViewController`（WT） |
| 11 | BMS | 4000–4999、30001 | `BMSUpgradeVer2ViewController` |

路由映射实现：`+[POFirmwareUpgradePromptBuilder routeTypeForDTUModel:]`（先 `isSocket` / `isBMS` …，否则 MainSystem）。

### 5.1 MainSystem 分支（与设置页一致）

```
isVer2Protocol?
  ├─ sceneType 1/2 或 energyViewType 2/3 → UpgradeRomoteSimpleViewController
  ├─ EFactionTypeSocket 独立插座 → UpgradeElementsViewController(Socket)
  └─ 默认 → BLEUpgradeVer2ViewController
否 → BLEUpgradeViewController
```

### 5.2 Socket 分支

```
energyViewType 2/3 → ESocketListViewController
否则 → UpgradeElementsViewController(Socket)
```

---

## 6. 调用方一览

| 场景 | 文件 | Builder | Navigator |
|------|------|---------|-----------|
| 设备首页 21000 弹窗 | `EMainBaseViewController` | `checkVersionWithPVSystem` | `loadSoftwareUpgrdeView` 点选 |
| 空间概览单机 | `SpaceOverviewUpgradeChecker` | `p_checkVersionWithPVSystem` | `p_presentFirmwareUpgradeSheetWithItems` 点选 |
| 设置 · 固件升级 | `EquipmentSettingViewController` | — | `POFirmwareUpgradeRouteTypeMainSystem` |
| 显示设置 · 升级 | `EquipmentDisplaySettingViewController` | — | `POFirmwareUpgradeRouteTypeMainSystem` |

### 6.1 设备主页弹窗附加逻辑（未下沉到 Builder）

- `p_shouldPresentFirmwareUpgradeSheetNow`：栈顶、无 modal 才弹
- `pendingFirmwareUpgradeItemArr`：异步回来时不在栈顶则延后，`viewDidAppear` 补弹
- `didChooseBlock` 内 `checkSleepStatus` 拦截
- `dismissFirmwareUpgradeReminderIfNeeded` / 与 pack 变更弹窗层级

### 6.2 空间概览附加逻辑

- `didPresentUpgradeReminderThisVisit`：同一次进入空间只提醒一次
- 弹窗挂在 `SpaceOverviewKeyWindowOverlayStack`

---

## 7. 接入示例

### 7.1 仅构建列表

```objc
#import "POFirmwareUpgradePromptBuilder.h"

NSArray<POTextModel *> *items =
    [POFirmwareUpgradePromptBuilder promptItemsFromDataModel:EQUIPMENTDATAHELPER.mainDataModel];
if (items.count == 0) {
    return;
}
// → 交给 POTextSelectedView 展示
```

### 7.2 点选后跳转

```objc
#import "POFirmwareUpgradeNavigator.h"

POTextModel *model = items[index];
if ([EQUIPMENTSETHELPER checkSleepStatus]) {
    return;
}
[POFirmwareUpgradeNavigator pushUpgradeViewControllerForRouteType:model.textId
                                             navigationController:self.navigationController];
```

### 7.3 设置页进主机升级

```objc
[POFirmwareUpgradeNavigator pushUpgradeViewControllerForRouteType:POFirmwareUpgradeRouteTypeMainSystem
                                             navigationController:self.navigationController];
```

---

## 8. 扩展指南

### 8.1 新增机型 ID

1. 在 `POFirmwareUpgradePromptBuilder.m` 中归入对应 tier（`po_isCommBoxSubID` / `po_isAccessorySubID` 或 tier 35/99）
2. 若需新升级页，在 `POFirmwareUpgradeRouteType` 增加枚举值
3. 在 `routeTypeForDTUModel:` 与 `POFirmwareUpgradeNavigator` 的 `switch` 补分支
4. 同步 Android 排序表与本节文档

### 8.2 修改 MainSystem 分支

改 `POFirmwareUpgradeNavigator` 的 `p_pushMainSystemUpgrade:`，并回归：

- 设置页固件升级
- 设备列表进升级（`UIView+SearchAndPush`，尚未接入 Navigator，逻辑应保持一致）
- 21000 弹窗点选主机项

### 8.3 不建议

- 在业务 VC 内再写一套 `po_sub*DTULists` + `break` 聚合
- 在 Builder 内 push VC（破坏 Helper 分层）

---

## 9. 真机回归建议

| 场景 | 关注 |
|------|------|
| 单机逆变器 | 本机一项；跳转 BLEUpgradeVer2 |
| AT1 + 子逆变器 | 本机 AT1 在前；多台逆变器均列出 |
| 多插座 | 每台 S1 独立一行；跳转 Socket 分支 |
| 外置电池多包 | tier 40 按序号；跳转 BMSUpgradeVer2 |
| Epanel | 协议 &lt; 2015 不弹；否则 Panel 升级页 |
| 并机盒子 | 子页不弹；回主后 deferred 补弹 |
| 空间概览 | 与设备主页列表顺序一致 |

---

## 10. 文件索引

```text
POModbus/Classes/POModbusHelper/Upgrade/
  POFirmwareUpgradePromptBuilder.h
  POFirmwareUpgradePromptBuilder.m

POModbus/Classes/POFunctionClasses/Upgrade/BLEUpgrade/
  POFirmwareUpgradeNavigator.h
  POFirmwareUpgradeNavigator.m

POModbus/Classes/POFunctionClasses/CommonSet/Controllers/
  EMainBaseViewController.m          ← checkVersionWithPVSystem

POModbus/Classes/POFunctionClasses/Space/Models/
  SpaceOverviewUpgradeChecker.m
```

---

## 11. 变更记录

| 日期 | 说明 |
|------|------|
| 2026/6/23 | 抽取 Builder + Navigator；排序与 Android 规范对齐；设置页接入统一跳转 |
