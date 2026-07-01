# POModbus Adapter 外部自定义规范

面向 **仅引 Core**、**部分替换默认实现** 或 **换云 / 换 UI / 换资源** 的接入方。  
架构总览见 [../POModbusSDK-Architecture.md](../POModbusSDK-Architecture.md)。  
SDK 使用速查见 [../08-POModbusSDK-Usage-and-Extension.md](../08-POModbusSDK-Usage-and-Extension.md)。

| 序号 | 文档 | 协议 / 类型 | 默认实现 |
|------|------|-------------|----------|
| 0 | [00-Bootstrap-CustomSpec.md](./00-Bootstrap-CustomSpec.md) | 注册入口 | `POModbusSDKBootstrap` |
| 1 | [01-MessageProviding-CustomSpec.md](./01-MessageProviding-CustomSpec.md) | `POModbusMessageProviding` | `POModbusDefaultMessageProvider` |
| 2 | [02-UIProviding-CustomSpec.md](./02-UIProviding-CustomSpec.md) | `POModbusUIProviding` | `POModbusToastUIProvider` |
| 3 | [03-CloudProviding-CustomSpec.md](./03-CloudProviding-CustomSpec.md) | `POModbusCloudProviding` | `POModbusMQTTCloudProvider` |
| 4 | [04-ResourceProviding-CustomSpec.md](./04-ResourceProviding-CustomSpec.md) | `POModbusResourceProviding` | `POModbusResourceBundleProvider` |
| 5 | [05-Configuration-CustomSpec.md](./05-Configuration-CustomSpec.md) | `POModbusSDKConfiguration` | `defaultConfiguration` |
| 6 | [06-ControlLoading-CustomSpec.md](./06-ControlLoading-CustomSpec.md) | `POControlLoadingState` / `EBaseProtocol` | `uiProvider` 或 `controlLoadingPresenter` |

## 快速对照

| 想改什么 | 看哪篇 |
|----------|--------|
| 启动怎么 register / 只换一项 Provider | 00 |
| 离线/超时/OTA 文案 | 01 |
| Toast、uiProvider 层 Loading | 02 |
| MQTT UTC、P12 下载、TOTP | 03 |
| beta plist、Bundle 资源路径 | 04 |
| 通道 Log 开关、PRO 不写 Logs DB | 05 |
| 控制写 Loading / 节流 / noLoadingOnce | **06** |

## 通用硬性规范

1. Provider 用 **static 强引用**（Context 为 weak）
2. 在 **Modbus/MQTT 连接前** register
3. 必需协议方法必须实现；optional 缺失有明确降级（见各文档）
4. 改 podspec `public_header` 后 App 需 `pod install` + Clean Build
