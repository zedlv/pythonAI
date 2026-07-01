# POModbusHelper 使用与功能扩展指南

> 面向：业务开发、Helper 维护者、精简 App 接入  
> SDK 基础：[08-POModbusSDK-Usage-and-Extension.md](./08-POModbusSDK-Usage-and-Extension.md)  
> 改造历程与测试：[07-POModbusHelper-Refactoring.md](./07-POModbusHelper-Refactoring.md)

---

## 1. 模块定位

**POModbusHelper** 位于 SDK Core 与 `POFunctionClasses` 之间，提供 **可复用的设备半业务能力**：

```text
POFunctionClasses（业务 UI）
        ↓ import
POModbusHelper
  ├── Connect/     连接、路由协议
  ├── Data/        会话数据、机型配置、认证
  ├── Status/      全局连接状态条
  ├── Protocol/    UI 门面、文案 key、控制 Loading 上下文
  ├── Search/      BLE 扫描
  ├── Upgrade/     OTA 封装与进度 UI
  ├── Interface/   关机/恢复出厂/日志浮窗/动画等组件
  └── Models/      EquipmentDataModel、EquipmentItemModel + DisplayStrings
        ↓
POModbusSDK Full
```

**设计原则**：Helper **不 import 业务 VC**；连接后跳转通过 `POEquipmentConnectRouting` 协议由 `POFunctionClasses` 或 App 实现。

---

## 2. 快速接入

### 2.1 Pod

```ruby
# 全量（Bluetti）
pod 'POModbus'

# 仅 Helper 层（自带 Full）
pod 'POModbus/POModbusHelper'

# 子模块按需
pod 'POModbus/POModbusHelper/Helper'    # Connect + Data + Status + Protocol
pod 'POModbus/POModbusHelper/Models'
pod 'POModbus/POModbusHelper/Search'
pod 'POModbus/POModbusHelper/Upgrade'
pod 'POModbus/POModbusHelper/Interface/Logs'
```

### 2.2 前置条件

```objc
[POModbusSDKBootstrap registerDefaultProviders];  // 或自研 Provider
```

未注册 Provider 时，`POHelperToast*` 可能回显 raw key 或走 POHUB fallback。

### 2.3 推荐 import

```objc
#import <POModbus/EquipmentConnectHelper.h>
#import <POModbus/EquipmentDataHelper.h>
#import <POModbus/POModbusHelperUI.h>
#import <POModbus/POHelperMessageKeys.h>
#import <POModbus/POEquipmentConnectRouting.h>
```

### 2.4 预编译头与 `POModbusCommonImports`

Pod 根目录（与 `POModbus.podspec` 同级）：

```text
POModbusCommonImports/POModbusCommonImports.h   # 共用 import
POModbusHelper-Prefix.pch                       # Helper 专用
POModbusFunctionClasses-Prefix.pch              # 业务层专用
```

| 文件 | 独有 import |
|------|-------------|
| `POModbusCommonImports.h` | POBase、POModbusBundle、POToast、POAlert、Masonry、MJExtension |
| `POModbusHelper-Prefix.pch` | `POModbusSDKFacade`、`POModbusHelperUI.h`；**不**注入 `POLocalizationBundle` |
| `POModbusFunctionClasses-Prefix.pch` | `POLocalizationBundle`（保留 `POLOCALSTRING`，P2-5 待迁） |

**SDK Core `.m` 勿依赖上述 PCH**；新增共用 import 只改 `POModbusCommonImports.h`。

---

## 3. 日常使用

### 3.1 设备连接 `EquipmentConnectHelper`

**列表 / 添加页进设备**：

```objc
[EquipmentConnectHelper connectEquipmentWithConfig:^EConnectConfig *(EConnectConfig *config) {
    config.connectFrom = EConnectFromCList;
    config.connectTo = EConnectToMain;           // 主页 / 配网 / 升级等
    config.deviceModel = model;
    config.connectChannel = EConnectChannelBLE;  // 或 MQTT
    config.pushAnimated = YES;
    return config;
}];
```

**`EConnectTo` 常用值**：

| 值 | 用途 |
|----|------|
| `EConnectToMain` | 设备主页 |
| `EConnectToWiFiConfig` | Wi-Fi 配网 |
| `EConnectToUpgrade` | 固件升级 |
| `EConnectToSystemConfig` | 房车系统配置 |
| `EConnectToExpertMode` | 安装商专家模式 |
| `EConnectToCallback` | 仅回调不跳转 |

连接成功后由已注册的 `POEquipmentConnectRouting` 实现跳转（默认 `POEquipmentConnectRoutingDefault`）。

**离开设备流程时断开**（列表、登录页、无网入口等）：

```objc
[EquipmentConnectHelper disconnectEquipmentConfig];
```

**回栈 / 退出**：

```objc
[EquipmentConnectHelper backToEquipmentListAction];
[EquipmentConnectHelper backToEquipmentMainAction];
[EquipmentConnectHelper backEquipmentAction];
[EquipmentConnectHelper jumpToEquipmentListAction];
```

### 3.2 会话数据 `EquipmentDataHelper`

单例宏：`EQUIPMENTDATAHELPER`（`[EquipmentDataHelper instanceSingleton]`）。

**使用前必须设置连接目标（二选一，BLE 优先）**：

```objc
EQUIPMENTDATAHELPER.currentPeripheral = peripheral;
// 或
EQUIPMENTDATAHELPER.currentEquipmentTopic = mqttTopic;
```

**机型能力**：`EQUIPMENTDATAHELPER.functionHelper`（`EquipmentFunctionHelper`）  
按 SN / 型号加载各 `hasSet*`、枚举列表、协议版本等。

**主数据模型**：`EQUIPMENTDATAHELPER.mainDataModel`（`EquipmentDataModel`）

**队列**：默认含 `POQueue_Main | POQueue_Control`；临时扩展 `POPROTOCOLREQUEST.queueOptions`，退出页时 `resetQueueOptionsType`。

### 3.3 UI 门面 `POModbusHelperUI`

Helper 内 **统一** 使用以下 API，不要新增 `POLOCALSTRING` / 裸 `POHUB`：

```objc
#import <POModbus/POModbusHelperUI.h>
#import <POModbus/POHelperMessageKeys+Connect.h>

// 固定 key（已本地化）
POHelperToast(POHelperMessageKeyListOffline);
POHelperToastSuccess(POHelperMessageKeyFactoryResetSuccess);
POHelperToastDelayed(POHelperMessageKeyBLEConnectFailed);
POHelperLoading(POHelperMessageKeyBLESearching);  // nil = 仅转圈
POHelperShowOffline();
POHelperDismissLoading();

// 动态文案
POHelperToastText(failedReason);
POHelperToastTextDelayed(failedReason);
POHelperToastTextTop(speechResult);   // 语音识别顶部提示

// Tier 2 字面量 key
POHelperLocalizedString(@"Config_Btn_confirm");
```

**文案策略**：

| 层级 | 用法 | 示例 |
|------|------|------|
| Tier 1 | 命名常量 + `messageProvider` | `POHelperToast(POHelperMessageKeyBLEOff)` |
| Tier 2 | `POHelperLocalizedString(@"key")` | 设置项、弹窗正文 |
| Tier 3 | Model Category | `-[EquipmentDataModel errorNameWithId:]` |
| **固定中文** | 常量即展示文案，**勿** `POModbusLocalizedString` | `POHelperMessageKeyGlobalStatusReady`（状态条，见 `+Status.h`） |

### 3.4 控制 Loading（P2-3）

业务主页 / 设置页基类在 `viewWillAppear` 安装：

```objc
POHelperInstallDefaultControlLoadingContext();
```

紧挨 **控制写** API 之前：

```objc
POHelperPrepareControlLoading(POHelperMessageKeySleepStateSleep);
[POPROTOCOLREQUEST setEquipmentCloseModeWithType:2];
```

| 路径 | API | HUD 时长 | 场景 |
|------|-----|----------|------|
| SDK 控制写 | `Prepare` + Request `loadingWhenControlAction` | 默认 1.5s 自动消失 | 休眠、关机、设置写 |
| Helper 读/连接 | `POHelperLoading` | ~24h 或手动 Dismiss | 读 PV/Grid、扫描、读基础信息 |

**不要**在控制写路径上再叠 `POHelperLoading`。

### 3.5 BLE 扫描 `BLEEquipmentSearchHelper`

由 `EquipmentConnectHelper` 内部调用；独立使用时注意 `POModbusLogChannelBLE` 开关（默认关，Debug 可开）。

### 3.6 OTA `*OTAHelper`

| 类 | 场景 |
|----|------|
| `BLEUpgradeOTAHelper` | 蓝牙 OTA |
| `POUpgradeOTAHelper` | 通用升级流程封装 |
| `RemoteUpgradeOTAHelper` | 远程 / MQTT OTA |

日志使用 `POModbusOTALog`（三门禁：非 PRO + Logs DB + `enableModbusOTALog`）。

### 3.7 Interface 组件

| 组件 | 用途 |
|------|------|
| `EquipmentCloseView` | 关机倒计时弹窗 |
| `EquipmentFactoryResetView` | 恢复出厂 |
| `POModbusLogsView` | Modbus 调试浮窗（`loadModbusLogsWithController:`） |
| `POEquipmentRealtimeStatusWindowPresenter` | 全局连接状态条（文案用 `POHelperMessageKeys+Status` 固定中文） |
| `EquipmentSpeechView` | 语音控制 |
| `PointLineAnimation` / `ArrowLineView` | 能量流动画 |

布局仍依赖 `POBASECONFIG` 间距/色值（PCH 注入 `POGlobalConfig`）。

### 3.8 Debug 工具（仅 `#if DEBUG`）

设备 **设置页**（`EquipmentSettingViewController`）导航栏：

| 按钮 | 页面 | 作用 |
|------|------|------|
| **Helper UI** | `POHelperUIDebugViewController` | Toast / 文案 / P2-3 Loading / P2-4 日志 |
| **Route** | `POEquipmentConnectRoutingDebugViewController` | 连接 Alert、各 `EConnectTo`、回栈 |

详见 [07 §10](./07-POModbusHelper-Refactoring.md#10-调试工具仅-if-debug-编译)。

---

## 4. 功能扩展

### 4.1 自定义连接后导航

实现 `POEquipmentConnectRouting`，注册覆盖默认：

```objc
#import <POModbus/POEquipmentConnectRouting.h>

@interface MyConnectRouter : NSObject <POEquipmentConnectRouting>
@end

@implementation MyConnectRouter

- (void)connectHelper:(EquipmentConnectHelper *)helper
navigateAfterConnectWithModel:(EquipmentItemModel *)model
                 config:(EConnectConfig *)config {
    switch (config.connectTo) {
        case EConnectToMain:
            // push 自研主页
            break;
        // …
    }
}

- (void)routingBackToEquipmentList {
    // pop / push 列表
}

@end

// AppDelegate 或测试启动
static MyConnectRouter *sRouter;
sRouter = [MyConnectRouter new];
[EquipmentConnectHelper registerRoutingDelegate:sRouter];
```

链 `POFunctionClasses` 时 `POEquipmentConnectRoutingDefault` 在 `+load` 自动注册；自定义须 **在首次连接前** register。

导航栈类名常量：`POEquipmentConnectRoutingTargets.h`（`EConnectPOPMainVC` 等）。

### 4.2 扩展 Toast / Loading 行为

**方式 A（推荐）**：实现 `POModbusUIProviding`，App 启动 register。Helper 的 `POHelperToast*` 优先走 `uiProvider`，缺失时 fallback POHUB。

**方式 B**：改 `POModbusHelperUI.m` 内 fallback（仅仓库内维护）。

`POHelperLoading` 使用 `maxDismissDuration: 24h`；控制写走 SDK 1.5s，二者勿混用。

### 4.3 新增 Helper 文案

1. 在 POLocalization 资源表加 key（与 App 一致）  
2. 高频 / 跨文件：在 `POHelperMessageKeys+*.h/.m` 增加 `FOUNDATION_EXPORT` 常量  
3. Helper 内使用 `POHelperToast(POHelperMessageKeyXxx)` 或 `POHelperLocalizedString`  
4. DEBUG：在 `POHelperUIDebugViewController` 增加可点击项  
5. **禁止** `POLOCALSTRING`；CI 可门禁 `rg POLOCALSTRING POModbus/Classes/POModbusHelper`

**固定中文**（不经多语言）：常量值直接写中文，调用处用常量本身，例如状态条四条 key（`+Status`）。

**批量迁移**（Helper 已迁完；P2-5 迁 `POFunctionClasses` 时复用）：

```bash
# 默认扫 POModbusHelper；迁业务层需改脚本内 ROOT 或加 --root
python3 scripts/migrate_polocalstring.py
```

规则与 `NAMED` 映射表见 [07 §9.11](./07-POModbusHelper-Refactoring.md#911-批量迁移脚本-scriptsmigrate_polocalstringpy)。

### 4.4 扩展控制 Loading

**改默认参数**（全局）：

```objc
void POHelperInstallDefaultControlLoadingContext(void) {
    // 见 POModbusHelperUI.m；可改 dismissDuration / debounceInterval
}
```

**单页定制**：

```objc
- (void)viewWillAppear:(BOOL)animated {
    [super viewWillAppear:animated];
    POHelperInstallDefaultControlLoadingContext();
    POPROTOCOLREQUEST.controlLoadingWillPresent = ^(POControlLoadingState *ctx) {
        ctx.dismissDuration = 2.5;
    };
}
```

`controlLoadingWillPresent` 参数类型为 **`POControlLoadingState *`**（非 `POControlLoadingContext`）。

**配图 HUD**：

```objc
#import <POModbus/POControlLoadingContext.h>

POPROTOCOLREQUEST.controlLoadingContext = [POControlLoadingContext defaultContext];
POPROTOCOLREQUEST.controlLoadingPresenter = ^(POControlLoadingState *ctx) {
    POControlLoadingContext *uiCtx = (POControlLoadingContext *)ctx;
    // 使用 uiCtx.iconImage、uiCtx.loadingText 自绘
};
```

### 4.5 新增机型配置

在 `EquipmentFunctionHelper.m` 增加 `loadXxxConfig`，在型号分发处注册。文案优先 `POHelperLocalizedString`，枚举用 `EItemModel modelWithCode:name:`。

### 4.6 新增 Interface 组件

1. 新建 `.h/.m` 于 `POModbusHelper/Interface/`  
2. podspec 补 subspec / `source_files`（若新目录）  
3. 布局可继续用 `POBASECONFIG`；长期可抽象 theme  
4. 用户可见文案走 `POHelperLocalizedString` / MessageKeys

### 4.7 日志扩展（P2-4）

Helper 内调试日志统一：

```objc
#import <POModbus/POModbusSDKLog.h>

POModbusLog(POModbusLogChannelBLE, @"scan %@", state);
POModbusOTALog(@"[BLE OTA] %@", phase);
```

不要新增裸 `POLog`。扫描类默认 `enableBLELog = NO`，联调时在 App 或 Debug 页打开。详见 [10-POModbus-Logging-System.md](./10-POModbus-Logging-System.md)。

### 4.8 精简 App（仅 Helper、无 POFunctionClasses）

```ruby
pod 'POModbus/POModbusHelper'
```

必须：

1. `registerDefaultProviders` 或自研 Provider  
2. `registerRoutingDelegate:` 实现全部 required / 用到的 optional 路由方法  
3. 自行实现设备主页 VC  
4. 自行处理 `POModbusBundle` 资源与本地化

---

## 5. 目录与职责速查

| 路径 | 职责 |
|------|------|
| `Helper/Connect/` | `EquipmentConnectHelper`、`POEquipmentConnectTypes`、`POEquipmentConnectRouting` |
| `Helper/Data/` | `EquipmentDataHelper`、`EquipmentFunctionHelper`、`EquipmentAuthenticaHelper` |
| `Helper/Status/` | 全局状态条 Session / Presenter |
| `Helper/Protocol/` | `POModbusHelperUI`、`POHelperMessageKeys`、`POControlLoadingContext`、Debug VC |
| `POModbusCommonImports/` | Helper / POFunctionClasses 共用 PCH import（Pod 根目录） |
| `Search/` | `BLEEquipmentSearchHelper` |
| `Upgrade/` | OTA Helper + 进度 View |
| `Interface/` | 关机、恢复出厂、Logs、语音、动画 |
| `Models/` | 数据模型 + `+DisplayStrings` |

---

## 6. 常见场景

| 场景 | 做法 |
|------|------|
| 列表点设备进主页 | `connectEquipmentWithConfig` + `EConnectToMain` |
| 离线仅配网 | ConnectHelper 内 Alert；Route Debug 可验文案 |
| 设置页写寄存器 | `viewWillAppear` Install Context + `Prepare` + Request |
| 读 PV 功率前转圈 | `POHelperLoading(nil)`，结束 `POHelperDismissLoading` |
| 换连接后跳转 | 自实现 `POEquipmentConnectRouting` |
| 加连接 Toast 文案 | `POHelperMessageKeys+Connect` + `POHelperToast` |
| Debug 验 P2-3 | 设置页 → Helper UI → controlLoadingContext Section |
| Debug 验 P2-4 日志 | 设置页 → Helper UI → 日志相关项 |
| Debug 验路由 | 设置页 → Route → navigateAfterConnect |

---

## 7. 后续扩展建议（维护者）

| 优先级 | 项 |
|--------|-----|
| P0 | `checkPVInfo` / `checkGridInfo` 失败路径补 `POHelperDismissLoading` |
| P1 | `POFunctionClasses` 文案迁 `POHelperLocalizedString`（P2-5） |
| P1 | 业务页 `POHUB` → `POHelperToast*` |
| P2 | Interface 主题脱 `POBASECONFIG` |
| P2 | `EquipmentFunctionHelper` 字面量升格命名 key |
| P3 | Debug 页可选「真写」控制项（需二次确认） |

完整清单见 [07 §12](./07-POModbusHelper-Refactoring.md#12-后续改造清单pomodbushelper--pomodbussdk)。

---

## 8. 相关文档

| 文档 | 内容 |
|------|------|
| [08-POModbusSDK-Usage-and-Extension.md](./08-POModbusSDK-Usage-and-Extension.md) | SDK 使用与 Provider 扩展 |
| [07-POModbusHelper-Refactoring.md](./07-POModbusHelper-Refactoring.md) | 分阶段改造、§10 Debug、§10.5 全覆盖测试 |
| [POModbusSDK-Architecture.md](./POModbusSDK-Architecture.md) | 总体架构 |
| [Adapter/06-ControlLoading-CustomSpec.md](./Adapter/06-ControlLoading-CustomSpec.md) | 控制 Loading 协议细节 |
| [10-POModbus-Logging-System.md](./10-POModbus-Logging-System.md) | 日志体系总览 |
