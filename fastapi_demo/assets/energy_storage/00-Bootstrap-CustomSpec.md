# Adapter 注册与 Bootstrap — 外部自定义规范

> 系列文档 0/6。总览见 [POModbusSDK-Architecture.md](../POModbusSDK-Architecture.md)。

---

## 1. 作用

`POModbusSDKBootstrap` 是 **Full/Adapter 层** 的一键注册入口，把四个默认 Provider 挂到 `POModbusSDKContext`：

| Provider | 默认类 |
|----------|--------|
| Message | `POModbusDefaultMessageProvider` |
| UI | `POModbusToastUIProvider` |
| Cloud | `POModbusMQTTCloudProvider` |
| Resource | `POModbusResourceBundleProvider` |

**仅引 Core 的工程没有 Bootstrap**，须自行实现协议并 register。

---

## 2. 默认用法（Bluetti）

```objc
#import <POModbus/POModbusSDKBootstrap.h>

// application:didFinishLaunchingWithOptions: 首行，早于 Modbus/MQTT 连接
[POModbusSDKBootstrap registerDefaultProviders];
```

- `dispatch_once`，重复调用无害。
- Bootstrap 内部用 **static 强引用** 持有四个 Provider（Context 上为 `weak`）。

---

## 3. 完全自定义 register

```objc
#import <POModbus/POModbusSDKFacade.h>

static MyMessageProvider *sMsg;
static MyUIProvider *sUI;
static MyCloudProvider *sCloud;
static MyResourceProvider *sRes;

+ (void)setupPOModbusSDK {
    sMsg = [MyMessageProvider new];
    sUI = [MyUIProvider new];
    sCloud = [MyCloudProvider new];
    sRes = [MyResourceProvider new];

    [[POModbusSDKContext shared] registerMessageProvider:sMsg
                                             uiProvider:sUI
                                          cloudProvider:sCloud
                                       resourceProvider:sRes
                                          configuration:nil];
}
```

### 3.1 硬性规范

| 规则 | 说明 |
|------|------|
| **强引用** | Provider 必须由 App / Bootstrap 的 static 或属性强持有，否则 register 后立刻释放 |
| **时机** | 任意 `POModbusLocalizedString`、MQTT 连接、控制 Loading 之前 |
| **线程** | 主线程 register（与 UI Provider、Loading 一致） |
| **configuration** | 传 `nil` 保留已有 `defaultConfiguration`；传实例则整体替换 |

### 3.2 部分替换（混用默认 + 自定义）

先 `registerDefaultProviders`，再 **单独 register** 只换一项（非 nil 项覆盖，nil 项跳过）：

```objc
[POModbusSDKBootstrap registerDefaultProviders];

static MyCloudProvider *sCloud;
sCloud = [MyCloudProvider new];
[[POModbusSDKContext shared] registerMessageProvider:nil
                                         uiProvider:nil
                                      cloudProvider:sCloud
                                   resourceProvider:nil
                                      configuration:nil];
```

---

## 4. 与 Configuration 配合

Bootstrap **不传** configuration 时，使用 `+[POModbusSDKConfiguration defaultConfiguration]`。

App 在 `loadBaseConfig` 等时机改字段即可（不必二次 register）：

```objc
POModbusSDKConfiguration *cfg = POModbusSDKContext.shared.configuration;
cfg.isProductionEnvironment = POBASECONFIG.isPROEnvironment;
cfg.enableMQTTLog = YES;
```

若 register 时传入自定义 `POModbusSDKConfiguration` 实例，会 **整体替换** Context 上的 configuration。详见 [05-Configuration-CustomSpec.md](./05-Configuration-CustomSpec.md)。

---

## 5. 依赖边界

| 集成方式 | Pod | 能否用 Bootstrap |
|----------|-----|------------------|
| Bluetti 全量 | `pod 'POModbus'` | ✅ |
| SDK + 默认桥接 | `pod 'POModbus/POModbusSDK/Full'` | ✅ |
| 纯 Core | `pod 'POModbus/POModbusSDK/Core'` | ❌ 须自实现四个协议 |

Bootstrap 依赖：`POLocalization`、`POBase`、`PONetwork`（Cloud 默认实现）。

---

## 6. 验收清单

- [ ] 启动后 `POModbusSDKContext.shared.messageProvider` 非 nil（或接受 key 回显）
- [ ] 离线一次 → 有 Toast 或自定义 UI（`enableSDKLog` 无 missing 日志）
- [ ] MQTT 连接 → UTC / 证书流程有 Cloud 日志或成功连上
- [ ] 协议 plist 能加载（Resource 或 Core bundle 回退）
- [ ] 控制写一次 → Loading 或 `controlLoadingPresenter` 生效

---

## 7. 相关文档

| 文档 | 内容 |
|------|------|
| [01-MessageProviding-CustomSpec.md](./01-MessageProviding-CustomSpec.md) | 文案 |
| [02-UIProviding-CustomSpec.md](./02-UIProviding-CustomSpec.md) | Toast / Loading |
| [03-CloudProviding-CustomSpec.md](./03-CloudProviding-CustomSpec.md) | MQTT UTC / 证书 |
| [04-ResourceProviding-CustomSpec.md](./04-ResourceProviding-CustomSpec.md) | plist / 图片 |
| [05-Configuration-CustomSpec.md](./05-Configuration-CustomSpec.md) | 日志 / 环境 |

相关头文件：`POModbusSDKBootstrap.h`、`POModbusSDKContext.h`。
