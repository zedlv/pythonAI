# Configuration — 外部自定义规范

> 系列文档 5/6。类型：`POModbusSDKConfiguration`  
> 入口：`POModbusSDKContext.shared.configuration`  
> 日志：`POModbusSDKLog.h`（含 `POModbusLogChannel` 枚举）

---

## 1. 作用

收敛原 **编译期** `POLogEnableConfig` 宏与部分 **POGlobalConfig / POBASECONFIG** 读取，改为 **运行时** 配置，App 可在启动时注入，Core 统一读取。

Bootstrap register 时传 `configuration:nil` 则使用 `+[POModbusSDKConfiguration defaultConfiguration]`。

---

## 2. 字段说明

### 2.1 日志开关（运行时）

| 属性 | channel | 主要模块 |
|------|---------|----------|
| `enableBLELog` | `POModbusLogChannelBLE` | POBLEManager |
| `enableMQTTLog` | `POModbusLogChannelMQTT` | POMQTTManager |
| `enableProtocolLog` | `POModbusLogChannelProtocol` | EBaseProtocol |
| `enableModbusLog` | `POModbusLogChannelModbus` | POProtocolRequest |
| `enableModbusOTALog` | `POModbusLogChannelModbusOTA` | EOTARequest |
| `enableModbusDataLog` | `POModbusLogChannelModbusData` | 数据解析 |
| `enablePushDataLog` | `POModbusLogChannelPushData` | MQTT Push |
| `enablePathLog` | `POModbusLogChannelPath` | POPathProtocol |
| `enablePathDataLog` | `POModbusLogChannelPathData` | Path 数据 |
| `enableSDKLog` | `POModbusLogChannelSDK` | Context / Provider |

打印示例：`POModbusLog(POModbusLogChannelMQTT, @"topic=%@", topic);`

默认值唯一来源：`+[POModbusSDKConfiguration configurationMatchingLegacyLogMacros]`。

输出走 **`POLog`**，受 App 非 PRO 环境约束；Bluetti 可 `BluettiDebugLogInstall` 落盘。

### 2.2 运行环境

| 属性 | 说明 |
|------|------|
| `isProductionEnvironment` | 对应 `POBASECONFIG.isPROEnvironment`；**YES 时不写 Modbus Logs DB**；OTA 调试日志额外受限 |

### 2.3 占位（后续迁入）

| 属性 | 说明 |
|------|------|
| `protocolRequestTimeout` | 秒；`0` = 沿用 Request 内部逻辑 |
| `bleWriteTimeout` | 秒；`0` = 沿用 POBLEManager 内部逻辑 |

---

## 3. App 注入方式

### 3.1 推荐：启动时改 shared configuration（Bluetti）

```objc
// AppDelegate+Config loadBaseConfig
POModbusSDKConfiguration *cfg = POModbusSDKContext.shared.configuration;
cfg.isProductionEnvironment = POBASECONFIG.isPROEnvironment;

#if DEBUG
cfg.enableMQTTLog = YES;
cfg.enableSDKLog = YES;
#endif
```

**无须**二次 register；改的是同一实例属性。

### 3.2 register 时传入副本

```objc
POModbusSDKConfiguration *cfg = [POModbusSDKConfiguration defaultConfiguration];
cfg.enableBLELog = YES;
[[POModbusSDKContext shared] registerMessageProvider:...
                                         uiProvider:...
                                      cloudProvider:...
                                   resourceProvider:...
                                      configuration:cfg];
```

会 **整体替换** Context 上的 configuration 对象。

### 3.3 自定义 Configuration 子类

不建议。如需扩展，在 App 层包装读写，或后续在 SDK 增加字段。

---

## 4. 与 Modbus Logs DB 浮窗的关系

Debug 浮窗「DB:开/关」控制的是 **`POModbusLogsDBManager.dbWriteEnabled`**，**不是** Configuration 字段。

写入 DB 两道门：

1. `isProductionEnvironment == YES` → **一律不写**（与 DB 开关无关）
2. `dbWriteEnabled == NO` → 不写

Configuration 与 Provider **无直接关系**；Logs DB 逻辑在 Core `POModbusLogsDBManager`。

---

## 5. 自定义要求清单

- [ ] PRO 包必须同步 `isProductionEnvironment`（Bluetti 已在 `loadBaseConfig`）
- [ ] Debug 按需打开通道 log，避免全开刷屏
- [ ] 不要改 `configurationMatchingLegacyLogMacros` 以外的地方维护「默认 0/1」编译宏
- [ ] 旧代码 `#import "POLogEnableConfig.h"` 仍可用（转发到 `POModbusSDKLog.h`）
- [ ] 新代码统一 `POModbusLog(POModbusLogChannel*, ...)`，开关改 Configuration
- [ ] `protocolRequestTimeout` / `bleWriteTimeout` 在未实现读取前设非 0 可能无效

---

## 6. 测试建议

1. Debug 开 `enableMQTTLog` → MQTT 连接有可读日志
2. PRO 环境 → Modbus Logs 浮窗开关无效（不写库）
3. 改 `enableSDKLog` → Provider missing 类日志可见

---

## 7. 相关头文件

`POModbusSDKConfiguration.h`、`POModbusSDKLog.h`、`POModbusSDKContext.h`

旧兼容：`POLogEnableConfig.h`（仅 import 转发）
