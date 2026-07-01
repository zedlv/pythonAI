# ControlLoading — 外部自定义规范

> 系列文档 6/6（业务 API，非 Provider 协议）。  
> 状态类型：`POControlLoadingState` / `POControlLoadingContext`  
> 入口：`POPROTOCOLREQUEST`（`[POProtocolRequest instanceSingleton]`，继承 `EBaseProtocol`）  
> HUD 渲染默认走 [02-UIProviding-CustomSpec.md](./02-UIProviding-CustomSpec.md)

---

## 1. 作用

控制类 Modbus **写指令**下发后，SDK 默认做两件事：

1. **队列节流**：写入 `queueSleepInterval`（间隔由 `controlQueueSleepInterval` 决定，默认 1.0s）
2. **HUD**：经 `controlLoadingPresenter` 或默认 `uiProvider` 展示 Loading

业务通过 **Request 单例上的属性** 定制，无需 import UIKit（Core 层）。

---

## 2. 触发条件

| 会触发 | 不会触发 |
|--------|----------|
| Request 内显式调用 `loadingWhenControlAction` 的控制写（如 `ESettingRequest` 部分 set） | 普通读操作 |
| | OTA 专用路径 |
| | 未调用 `loadingWhenControlAction` 的 set |

---

## 3. 类型说明

### POControlLoadingState（Core）

| 属性 | 默认值（`defaultContext`） | 含义 |
|------|---------------------------|------|
| `text` | `nil` | 文案；nil 仅转圈 |
| `dismissDuration` | `1.5` | 最长展示秒数 |
| `showsHUD` | `YES` | 是否弹 HUD |
| `debounceInterval` | `0.25` | 短时间去重；`0` 不去重 |

### POControlLoadingContext（Helper，可选）

继承 `POControlLoadingState`，增加 `iconImage`。  
默认 `uiProvider` **不消费** `iconImage`；配图须在 `controlLoadingPresenter` 内读取。

```objc
#import <POModbus/POControlLoadingContext.h>

POPROTOCOLREQUEST.controlLoadingContext = [POControlLoadingContext defaultContext];
```

---

## 4. EBaseProtocol / POPROTOCOLREQUEST API

| 成员 | 作用域 | 说明 |
|------|--------|------|
| `controlLoadingContext` | 长期 | 默认 Loading 参数（`POControlLoadingState` 实例） |
| `prepareControlLoadingText:` | **下一次** | 便捷设一次性文案 |
| `controlLoadingWillPresent` | **下一次** | 展示前改 context，执行后自动 `nil` |
| `controlLoadingPresenter` | 长期 | 完全自定义 HUD，**不走** `uiProvider` |
| `noLoadingOnce` | **下一次** | 跳过节流 + HUD，用后自动 `NO` |
| `controlQueueSleepInterval` | 长期 | 节流间隔（秒），默认 `1.0` |

`queueSleepInterval` 由 SDK 在 `loadingWhenControlAction` 内写入，业务一般勿改。

---

## 5. 三条自定义路径

```text
控制写 → loadingWhenControlAction
           │
           ├─ noLoadingOnce? → 直接 return（无节流、无 HUD）
           │
           ├─ 写 queueSleepInterval（除非 noLoadingOnce）
           │
           ├─ showsHUD == NO 或 dismissDuration <= 0 → 仅节流，不弹 HUD
           │
           ├─ debounce 去重
           │
           ├─ controlLoadingWillPresent（一次性，用后 nil）
           │
           ├─ controlLoadingPresenter 有值?
           │     └─ YES → 调 presenter，结束
           │
           └─ NO → Context showControlLoading* → uiProvider
```

| 路径 | 适用场景 |
|------|----------|
| 改 `controlLoadingContext` / 一次性 API | 只改文案、时长、去重 |
| 改 `uiProvider`（见文档 02） | App 级统一 HUD 样式（POHUB 等） |
| 设 `controlLoadingPresenter` | 单次或长期完全自绘（含配图） |
| `noLoadingOnce` | 业务自有 Loading（如 CT 检测） |

---

## 6. noLoadingOnce vs showsHUD

| | 队列节流 | HUD |
|--|:--------:|:---:|
| 默认 | ✅ | ✅ |
| `controlLoadingContext.showsHUD = NO` | ✅ | ❌ |
| `noLoadingOnce = YES`（仅下一次） | ❌ | ❌ |

---

## 7. 使用示例

### 7.1 默认（推荐）

```objc
[POPROTOCOLREQUEST setAlternatorControlMode:1];
// 1.0s 节流 + 1.5s 无文案转圈
```

### 7.2 仅下一次改文案

```objc
[POPROTOCOLREQUEST prepareControlLoadingText:@"开机中"];
[POPROTOCOLREQUEST setAlternatorEnable:YES];
```

### 7.3 仅下一次改多项

```objc
POPROTOCOLREQUEST.controlLoadingWillPresent = ^(POControlLoadingState *ctx) {
    ctx.text = @"关机中";
    ctx.dismissDuration = 2.0;
};
[POPROTOCOLREQUEST setAlternatorEnable:NO];
```

### 7.4 App 全局默认

```objc
POPROTOCOLREQUEST.controlLoadingContext.text = @"设置中…";
POPROTOCOLREQUEST.controlLoadingContext.dismissDuration = 2.0;
[POPROTOCOLREQUEST setACInputMode:0];
```

### 7.5 完全自定义 HUD（长期）

```objc
POPROTOCOLREQUEST.controlLoadingPresenter = ^(POControlLoadingState *ctx) {
    if (ctx.text.length) {
        [POHUB showLoadingWithText:ctx.text maxDismissDuration:ctx.dismissDuration dismissBlock:nil];
    } else {
        [POHUB showLoadingWithDismissDuration:ctx.dismissDuration];
    }
};
```

带配图：

```objc
POPROTOCOLREQUEST.controlLoadingContext = [POControlLoadingContext defaultContext];
POPROTOCOLREQUEST.controlLoadingPresenter = ^(POControlLoadingState *ctx) {
    POControlLoadingContext *uiCtx = [ctx isKindOfClass:[POControlLoadingContext class]] ? (POControlLoadingContext *)ctx : nil;
    // 使用 uiCtx.iconImage
};
```

### 7.6 业务自有 Loading

```objc
[POHUB showLoadingWithText:@""];
POPROTOCOLREQUEST.noLoadingOnce = YES;
[POPROTOCOLREQUEST setCTCheckActionSuccessBlock:^(NSData *data, NSInteger content) {
    // ...
} errorBlock:^(NSInteger code, NSString *reason) {
    // ...
}];
```

### 7.7 只要节流、不要 HUD

```objc
POPROTOCOLREQUEST.controlLoadingContext.showsHUD = NO;
[POPROTOCOLREQUEST setAlternatorControlMode:1];
```

---

## 8. 前置条件与降级

| 条件 | 行为 |
|------|------|
| 未 `registerDefaultProviders` 且 uiProvider 无 Loading 方法 | **只打日志**，不弹 HUD；节流仍可能生效 |
| 已 register + `POModbusToastUIProvider` | 默认 POHUB Loading |
| 设了 `controlLoadingPresenter` | **不再**调 uiProvider |

---

## 9. 自定义要求清单

- [ ] 启动时已 `[POModbusSDKBootstrap registerDefaultProviders]`（或自实现 uiProvider 的 `showLoading*`）
- [ ] `noLoadingOnce` 须在 **主线程**、**紧挨**下一次控制 API 之前设置；勿在中间插入其它写操作
- [ ] `controlLoadingWillPresent` / `prepareControlLoadingText:` 仅影响 **紧接着的一次** 控制写
- [ ] 长期 presenter 与 uiProvider 勿重复叠两层 HUD
- [ ] 成功 Toast 由业务自行处理（SDK 控制 Loading 不含成功提示）
- [ ] 滑杆连发等场景 Request 层可能内部设 `noLoadingOnce`，业务一般无需重复

---

## 10. 仓库内参考

| 文件 | 用法 |
|------|------|
| `EAdvancedSetBaseViewController.m` | 自有 CT 检测 Loading + `noLoadingOnce` |
| `EDisplaySettingController.m` | `POHUB` + `noLoadingOnce` 后读 BLE MAC |

---

## 11. 测试建议

1. 普通设置项控制写 → 默认 Loading + 节流
2. `prepareControlLoadingText:` → 仅下一次有文案
3. `showsHUD = NO` → 无弹窗，写指令仍节流
4. `noLoadingOnce` → 无弹窗、无节流
5. 快速连点同一控制 → debounce 生效（0.25s 内不重复 HUD）
6. 未 register uiProvider → 无 HUD，SDK 日志可见

---

## 12. 相关头文件

| 头文件 | 说明 |
|--------|------|
| `POControlLoadingState.h` | Core 状态 + 头内速查 |
| `POControlLoadingContext.h` | Helper 配图扩展 |
| `EBaseProtocol.h` | 属性声明 |
| `POProtocolRequest.h` | 单例入口 |
| `POModbusUIProviding.h` | 默认 HUD 协议（文档 02） |
