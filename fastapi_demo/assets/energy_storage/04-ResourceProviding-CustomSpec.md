# ResourceProviding — 外部自定义规范

> 系列文档 4/6。协议：`POModbusResourceProviding.h`  
> 默认实现：`POModbusResourceBundleProvider`（Adapter → `POModbusBundle`）

---

## 1. 作用

Core 读取协议 plist、部分资源时，不直接依赖 `POModbusBundle` Pod 资源类，而走 **Provider → Core bundle 回退**。

```
POModbusSDKContext pathForResourceName:fileType:
  ① resourceProvider pathForResourceName:fileType:
  ② 未命中 → POModbusSDKCore.bundle（POModbusSDKCoreResource）
```

---

## 2. 协议 API

### 必需

```objc
- (nullable NSString *)pathForResourceName:(NSString *)name fileType:(NSString *)fileType;
```

| 要求 | 说明 |
|------|------|
| 返回值 | 资源 **绝对路径**；找不到返回 `nil` 触发 Core 回退 |
| 典型调用 | `name=@"POModbusBetaProtocol"` `fileType=@"plist"` |
| 线程 | 同步、快速（读 bundle 路径，勿网络） |

### 可选（需 UIKit）

```objc
- (nullable UIImage *)imageNamed:(NSString *)name;
```

默认实现：`POMODBUSIMAGE(name)`。Core 协议解析 **主要用 path**，图片多为业务层宏。

---

## 3. 默认实现

```objc
// POModbusResourceBundleProvider
- (NSString *)pathForResourceName:(NSString *)name fileType:(NSString *)fileType {
    return [[POModbusBundle instanceSingleton] po_filePathForName:name fileType:fileType];
}

- (UIImage *)imageNamed:(NSString *)name {
    return POMODBUSIMAGE(name);
}
```

资源来自 Pod **`POModbusBundle`**（Assets 下 xcassets、JSON、ProtocolFiles 等）。

---

## 4. Core bundle 回退

| 资源 | 位置 |
|------|------|
| `POModbusBetaProtocol.plist` | `POModbusSDKCore.bundle`（`Core/Resources/`） |
| 仅引 Core、无 App Bundle | 依赖回退仍可解析 beta 协议 |

Provider 返回 nil 时 `POModbusLog(POModbusLogChannelSDK, ...)`，再查 Core bundle。

---

## 5. 自定义示例

### 5.1 指向 App 主 Bundle

```objc
@implementation MyResourceProvider

- (NSString *)pathForResourceName:(NSString *)name fileType:(NSString *)fileType {
    return [[NSBundle mainBundle] pathForResource:name ofType:fileType];
}

@end
```

### 5.2 多 bundle 优先级

```objc
- (NSString *)pathForResourceName:(NSString *)name fileType:(NSString *)fileType {
    NSString *path = [[MySDKBundle bundle] pathForResource:name ofType:fileType];
    if (path.length) return path;
    return [[NSBundle mainBundle] pathForResource:name ofType:fileType];
}
```

### 5.3 动态下发 plist（高级）

可缓存到 Caches 后返回绝对路径；须保证 Core 读取期间文件存在。

---

## 6. 双份 plist 维护

| 副本 | 用途 |
|------|------|
| `Assets/ProtocolFiles/POModbusBetaProtocol.plist` | 业务/历史真源，打进 `POModbusBundle` |
| `Core/Resources/POModbusBetaProtocol.plist` | 打进 `POModbusSDKCore.bundle`，Core-only 回退 |

**修改协议映射时须同步两处**（或 Provider 只指向一处真源）。

---

## 7. 自定义要求清单

- [ ] `pathForResourceName:fileType:` 必须实现
- [ ] 对 Core 依赖的 plist 至少保证一条路径可命中（Provider 或 Core bundle）
- [ ] 返回路径文件必须存在且可读
- [ ] 不要在 Provider 内做耗时 IO 以上操作
- [ ] `imageNamed:` 可选；业务图片仍可用 `POModbusBundle.h` 宏（App 层）
- [ ] 强引用持有 Provider

---

## 8. 与 POModbusBundle 的关系

| 场景 | 建议 |
|------|------|
| Bluetti 全量 Pod | 默认 `POModbusResourceBundleProvider` 即可 |
| 仅 Core + 自研 App | 自定义 Provider 或依赖 Core bundle 回退 |
| App import | `#import <POModbus/POModbusBundle.h>`（Adapter public header） |

---

## 9. 测试建议

1. 冷启动解析设备协议字段正常（beta plist 加载）
2. Provider 故意返回 nil → Core bundle 仍能工作
3. 替换 Provider 指向测试 plist → 字段映射变化生效

---

## 10. 相关头文件

`POModbusResourceProviding.h`、`POModbusSDKContext+Resource.h`、`POModbusSDKCoreResource.h`、`POModbusBundle.h`
