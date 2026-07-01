# MessageProviding — 外部自定义规范

> 系列文档 1/6。协议：`POModbusMessageProviding.h`  
> 默认实现：`POModbusDefaultMessageProvider`（Adapter → `POLocalization`）

---

## 1. 作用

Core 内所有用户可见文案通过 **`POModbusLocalizedString(key)`** 获取，不直接 `#import POLocalization`。

```
Core 代码
  → POModbusLocalizedString(POModbusMessageKeyOffline)
    → POModbusSDKContext.messageProvider
      → -messageForKey:
```

---

## 2. 协议 API

### 必需

```objc
- (NSString *)messageForKey:(NSString *)key;
```

| 要求 | 说明 |
|------|------|
| `key` | 与 `POModbusMessageKeys.h` / POLocalization 资源表一致，如 `@"E_Main_offline"` |
| 返回值 | 本地化后的字符串；key 不存在时建议回传 `defaultValue` 或 key 本身 |
| 空 key | 返回 `@""` |

### 可选

```objc
- (NSString *)messageForKey:(NSString *)key defaultValue:(NSString *)defaultValue;
```

`POModbusLocalizedString` 优先走带 `defaultValue` 的方法；未实现则只调 `messageForKey:`。

---

## 3. 默认实现行为

```objc
// POModbusDefaultMessageProvider
- (NSString *)messageForKey:(NSString *)key {
    return POLOCALSTRING(key);
}
```

---

## 4. 自定义示例

### 4.1 自建本地化表

```objc
@implementation MyMessageProvider

- (NSString *)messageForKey:(NSString *)key {
    if (!key.length) return @"";
    NSString *text = [[MyL10n bundle] localizedStringForKey:key value:nil table:nil];
    return text.length ? text : key;
}

- (NSString *)messageForKey:(NSString *)key defaultValue:(NSString *)defaultValue {
    NSString *text = [self messageForKey:key];
    return text.length ? text : (defaultValue ?: key);
}

@end
```

### 4.2 包装 POLocalization（与默认等价）

直接复用 `POModbusDefaultMessageProvider` 或 copy 其实现即可。

### 4.3 固定英文 / 调试

```objc
- (NSString *)messageForKey:(NSString *)key {
    return key; // 或 return @"[Modbus]"; 仅调试
}
```

---

## 5. Key 规范

| 来源 | 说明 |
|------|------|
| `POModbusMessageKeys.h` | Core 使用的常量，行尾注释为资源表原始 key |
| 新增 key 流程 | ① Keys.h 加常量 ② Core 使用 ③ POLocalization 加翻译 ④ 自定义 Provider 能解析该 key |
| `POModbusMakeError` | NSError 的 `userInfo[POModbusMessageUserInfoKey]` 存原始 key，便于业务二次本地化 |

---

## 6. 未注册 / 失败行为

| 场景 | 行为 |
|------|------|
| 未 register messageProvider | 回传 **key 本身**，`POModbusLog(POModbusLogChannelSDK, ...)`（需 `enableSDKLog`） |
| Provider 返回空串 | 回传 key，`POModbusLog(POModbusLogChannelSDK, ...)` |

---

## 7. 自定义要求清单

- [ ] 实现 `messageForKey:`，同步返回（勿阻塞主线程做网络）
- [ ] 覆盖 `POModbusMessageKeys.h` 中 Core 用到的全部 key（至少离线、超时、OTA 相关）
- [ ] 与 App 语言切换策略一致（若 App 切语言需刷新，Provider 内读当前 locale）
- [ ] 不建议在 Provider 内弹 UI；只负责字符串
- [ ] 强引用持有 Provider 实例

---

## 8. 测试建议

1. 断网离线 → 提示文案是否为预期语言（非 raw key）
2. OTA 失败 → 错误 NSError 的 `localizedDescription` 可读
3. 关闭 Provider（nil）→ 日志有 `messageProvider missing`，界面显示 key

---

## 9. 相关头文件

`POModbusMessageProviding.h`、`POModbusMessageKeys.h`、`POModbusSDKLocalization.h`
