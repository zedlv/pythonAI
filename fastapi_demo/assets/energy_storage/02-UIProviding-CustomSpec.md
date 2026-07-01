# UIProviding — 外部自定义规范

> 系列文档 2/6。协议：`POModbusUIProviding.h`  
> 默认实现：`POModbusToastUIProvider`（Adapter → `POHUB` / POToast）  
> 控制 Loading 业务 API 另见 [06-ControlLoading-CustomSpec.md](./06-ControlLoading-CustomSpec.md)

---

## 1. 作用

Core 不 import UIKit / POToast。短提示、离线 Toast、**控制下发 Loading** 经 `POModbusSDKContext (UI)` → `uiProvider`。

```
EBaseProtocol.loadingWhenControlAction
  → controlLoadingPresenter?（业务长期自定义）
  → 默认：Context showControlLoading*
    → uiProvider showLoading*
```

---

## 2. 协议 API

### 必需

```objc
- (void)showMessage:(NSString *)text;
```

空字符串 **不调用** 或内部忽略。

### 可选（强烈建议实现）

| 方法 | Core 调用场景 | 缺失时行为 |
|------|---------------|------------|
| `showOfflineMessage` | 设备离线 | 默认 Provider 本地化 offline 后 `showMessage:`；Context 走 `showMessageForKey:` |
| `showSuccessfulMessage:` | 成功类提示 | 无统一降级，需自行在 Provider 实现 |
| `showLoadingWithText:maxDismissDuration:` | 控制写 Loading（有文案） | **仅打日志**，不弹 UI |
| `showLoadingWithMaxDismissDuration:` | 控制写 Loading（无文案） | **仅打日志** |
| `showMessageAfterDelay:` | 延迟失败提示 | 降级为立即 `showMessage:` |

---

## 3. 默认实现映射

| 协议方法 | POHUB |
|----------|-------|
| `showMessage:` | `showText:` |
| `showSuccessfulMessage:` | `showSuccessfulText:` |
| `showLoadingWithText:...` | `showLoadingWithText:maxDismissDuration:dismissBlock:` |
| `showLoadingWithMaxDismissDuration:` | `showLoadingWithDismissDuration:` |
| `showMessageAfterDelay:` | `afterDelayToShowText:` |

---

## 4. 自定义示例

### 4.1 最小实现（仅 Toast）

```objc
@implementation MyUIProvider

- (void)showMessage:(NSString *)text {
    if (!text.length) return;
    [MyToast show:text];
}

@end
```

⚠️ 不实现 Loading 方法时，**控制下发默认 HUD 不会出现**（队列节流仍生效，除非 `noLoadingOnce`）。

### 4.2 完整实现（含 Loading）

```objc
- (void)showLoadingWithText:(NSString *)text maxDismissDuration:(NSTimeInterval)maxDismissDuration {
    [MyHUD showLoading:text duration:maxDismissDuration];
}

- (void)showLoadingWithMaxDismissDuration:(NSTimeInterval)maxDismissDuration {
    [MyHUD showSpinner:maxDismissDuration];
}

- (void)showOfflineMessage {
    [self showMessage:NSLocalizedString(@"device_offline", nil)];
}
```

### 4.3 业务层绕过 uiProvider（控制 Loading）

在 **Request 单例**上设 presenter，**不再**走 uiProvider：

```objc
POPROTOCOLREQUEST.controlLoadingPresenter = ^(POControlLoadingState *ctx) {
    // 完全自定义 HUD
};
```

详见 [06-ControlLoading-CustomSpec.md](./Adapter/06-ControlLoading-CustomSpec.md)：`prepareControlLoadingText:`、`noLoadingOnce`、`showsHUD` 等。

---

## 5. Context 便捷 API（供 Core 调用）

| 方法 | 说明 |
|------|------|
| `showMessageForKey:` | 先本地化再 `showMessage:` |
| `showOfflineMessage` | `POModbusMessageKeyOffline` |
| `showControlLoadingWithText:maxDismissDuration:` | 控制 Loading |
| `showControlLoadingWithMaxDismissDuration:` | 控制 Loading 无文案 |
| `showMessageAfterDelay:` | 延迟提示 |

uiProvider 为 nil 时：**只打 `POModbusLog(POModbusLogChannelSDK, ...)`**，无静默兜底。

---

## 6. 自定义要求清单

- [ ] **主线程**展示 UI（Core 多在主线程调 Context，Provider 内勿强制后台弹窗）
- [ ] `showMessage:` 必须实现
- [ ] 若使用默认控制 Loading 路径，必须实现两个 `showLoading*` 方法
- [ ] Loading 的 `maxDismissDuration` 为 **最长** 展示时间，非固定时长
- [ ] 不与 `POPROTOCOLREQUEST.controlLoadingPresenter` 重复叠两层 HUD（二选一）
- [ ] 强引用持有 Provider

---

## 7. 与控制 Loading 的关系

| 层级 | 职责 |
|------|------|
| `POControlLoadingState` | 文案 / 时长 / 是否 HUD / 去重（Core） |
| `POPROTOCOLREQUEST.*` | 业务改参数、`noLoadingOnce` |
| `uiProvider` | 默认 HUD 渲染 |
| `controlLoadingPresenter` | 业务完全接管 HUD |

---

## 8. 测试建议

1. 设备离线 → Toast 出现
2. 设置页任意控制写 → Loading 出现并在超时后消失
3. `showsHUD = NO` → 无 Loading，仍有节流
4. `noLoadingOnce = YES` → 无 Loading、无节流
5. 未 register uiProvider → 无 UI，SDK 日志可见

---

## 9. 相关头文件

`POModbusUIProviding.h`、`POModbusSDKContext+UI.h`、`POControlLoadingState.h`、`EBaseProtocol.h`
