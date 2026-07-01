# iOS IoT 学习文档与 Demo（桌面）

| 资源 | 路径 | 说明 |
|------|------|------|
| 蓝牙异常全方案 | [iOS-BLE-Exception-Handling.md](./iOS-BLE-Exception-Handling.md) | 对照 POModbus 生产代码 |
| WiFi 配网全方案 | [iOS-WiFi-Provisioning.md](./iOS-WiFi-Provisioning.md) | SoftAP / SmartConfig / **本项目 BLE 写寄存器** |
| 极简 Demo | [BLEWiFiDemo/](./BLEWiFiDemo/) | 扫描连接 + CRC + 心跳 + SoftAP Mock |
| 3 分钟演示稿 | [BLEWiFiDemo/Demo-Guide.md](./BLEWiFiDemo/Demo-Guide.md) | 面试口述脚本 |
| 月末自测 FAQ | [iOS-IoT-Monthly-FAQ.md](./iOS-IoT-Monthly-FAQ.md) | 蓝牙 7 题 + WiFi 3 题标准答 |

## 快速开始 Demo

1. 打开 [BLEWiFiDemo/README.md](./BLEWiFiDemo/README.md) 按步骤新建 Xcode 工程  
2. 拖入 `BLEWiFiDemo/BLEWiFiDemo/**/*.m`  
3. 合并 `BWAppDelegate.m.example`、补充 `Info.plist.example` 权限  

## 与 Git 仓库关系

- 生产代码：`~/Desktop/Git/pomodbus`  
- 本目录为 **学习沉淀副本**，可独立阅读，不依赖 CocoaPods  
