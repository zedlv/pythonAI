# CloudProviding — 外部自定义规范

> 系列文档 3/6。协议：`POModbusCloudProviding.h`  
> DTO：`POModbusMQTTUTCInfo` / `POModbusMQTTTLSMaterials`  
> 默认实现：`POModbusMQTTCloudProvider`（Adapter → POAskManager + PODownloadManager）

---

## 1. 作用

MQTT 连接前需要：**服务器 UTC**、**客户端 P12 证书**、**MQTT 用户名密码**。Core 的 `POMQTTManager` 只调 `POModbusSDKContext (Cloud)`，不依赖 `POAskManager`。

```
POMQTTManager 连接流程
  ① fetchMQTTUTCInfoWithCompletion:
  ② prepareMQTTTLSMaterialsWithUTCInfo:accessToken:...
  ③ 使用 POModbusMQTTTLSMaterials 建立 TLS
  ④ 连接成功后 cleanupMQTTCertDownloadWithURL:
```

---

## 2. 协议 API

### 必需

#### ① 拉取 UTC

```objc
- (void)fetchMQTTUTCInfoWithCompletion:(void (^)(POModbusMQTTUTCInfo *info, NSError *error))completion;
```

#### ② 准备 TLS 材料

```objc
- (void)prepareMQTTTLSMaterialsWithUTCInfo:(POModbusMQTTUTCInfo *)utcInfo
                               accessToken:(NSString *)accessToken
                                accessCode:(nullable NSString *)accessCode
                                  clientId:(NSString *)clientId
                                iotAddress:(NSString *)iotAddress
                                completion:(void (^)(POModbusMQTTTLSMaterials *materials, NSError *error))completion;
```

| 入参 | 说明 |
|------|------|
| `accessToken` | 格式 `tokenCode.account`（JWT 前两段），Adapter 用于 TOTP / tid |
| `accessCode` | 非空时密码为 `rmt:accessCode`，否则 TOTP |
| `clientId` | 设备/client 标识，参与 PFX 请求签名 |
| `iotAddress` | broker 地址，用于选择 CA |

### 可选

```objc
- (NSString *)defaultMQTTIoTAddress;  // 默认 [POAPI rootIoT]
- (void)cleanupMQTTCertDownloadWithURL:(NSString *)downloadURL;
```

---

## 3. DTO 字段规范

### POModbusMQTTUTCInfo（fetch 产出）

| 字段 | 必填 | 说明 |
|------|------|------|
| `utcInterval` | ✅ | UTC **秒**级时间戳 |
| `signature` | ✅* | 解密 P12 口令（Bluetti 算法必填） |
| `serverIoT` | 否 | 覆盖 MQTT 地址 |
| `connToken` | 否 | 扩展 |
| `expires` | 否 | 过期信息 |

Adapter 默认 JSON 映射（`+utcInfoFromResponse:`）：

- `value` → `utcInterval`
- `X-Signature` / `signature` → `signature`
- `serverIoT`、`connToken`、`X-Expires` / `expires`

### POModbusMQTTTLSMaterials（prepare 产出）

| 字段 | 必填 | 说明 |
|------|------|------|
| `mqttUser` | ✅ | 默认 `tid:账号` |
| `mqttPassword` | ✅ | `rmt:...` 或 TOTP 串 |
| `clientCertPath` | ✅ | p12 **本地绝对路径** |
| `clientCertPassphrase` | ✅ | p12 口令 |
| `caCertData` | 建议 | CA 的 der 数据；nil 时 Manager 可能无 CA |
| `certDownloadURL` | 建议 | 供 cleanup 删除缓存文件 |

---

## 4. 默认实现（Bluetti 对齐）

| 步骤 | 接口 | 实现要点 |
|------|------|----------|
| UTC | `GET /cert/app/v2/now/utc-time` | `POAskManager` + `POModbusAskMQTTUTCRequest` |
| PFX | `POST .../cert/app/v1/pfx` | 树排序 MD5 + AES 加密 header，`PODownloadManager` 落盘 |
| 密码 | TOTP | `pom_totpWithTokenCode:tokenId:utcTime:`（见 Provider 私有方法） |
| CA | 主包资源 | `CA-PRO.der` / `CA-DEV.der` 按 IoT 环境选择 |

**完全自建云**时可换 URL/鉴权，只要 DTO 满足上表即可。

---

## 5. 自定义示例骨架

```objc
@implementation MyCloudProvider

- (void)fetchMQTTUTCInfoWithCompletion:(void (^)(POModbusMQTTUTCInfo *, NSError *))completion {
    [MyHTTP GET:@"/your/utc" completion:^(NSDictionary *json, NSError *err) {
        if (err) { completion(nil, err); return; }
        POModbusMQTTUTCInfo *info = [POModbusMQTTUTCInfo new];
        info.utcInterval = [json[@"ts"] doubleValue];
        info.signature = json[@"sig"];
        completion(info, nil);
    }];
}

- (void)prepareMQTTTLSMaterialsWithUTCInfo:(POModbusMQTTUTCInfo *)utcInfo
                               accessToken:(NSString *)accessToken
                                accessCode:(NSString *)accessCode
                                  clientId:(NSString *)clientId
                                iotAddress:(NSString *)iotAddress
                                completion:(void (^)(POModbusMQTTTLSMaterials *, NSError *))completion {
    // 下载 p12、计算 mqttUser/mqttPassword、填 materials
    POModbusMQTTTLSMaterials *m = [POModbusMQTTTLSMaterials new];
    m.mqttUser = @"...";
    m.mqttPassword = @"...";
    m.clientCertPath = downloadedPath;
    m.clientCertPassphrase = @"...";
    m.caCertData = [NSData dataWithContentsOfFile:caPath];
    m.certDownloadURL = downloadURL;
    completion(m, nil);
}

- (void)cleanupMQTTCertDownloadWithURL:(NSString *)downloadURL {
    [[NSFileManager defaultManager] removeItemAtPath:cachedPath error:nil];
}

@end
```

---

## 6. 错误规范

| 建议 | 说明 |
|------|------|
| domain | `POModbusCloud` 或 App 自定义 |
| code | HTTP status 或 `-1` 业务错误 |
| `NSLocalizedDescriptionKey` | 可读原因，会出现在 MQTT 连接失败链路 |
| 异步 | **必须**回调 completion（成功/失败），勿悬空 |

未注册 cloudProvider：Context 返回 `POModbusSDK` domain code `-1`。

---

## 7. 自定义要求清单

- [ ] 两个必需方法均实现
- [ ] `fetch` 失败时 `completion(nil, error)`，勿传半空 `POModbusMQTTUTCInfo`
- [ ] p12 文件在 MQTT 连接完成前保持有效
- [ ] 实现 `cleanupMQTTCertDownloadWithURL:` 或在 prepare 中使用可复用路径策略
- [ ] 与 Bluetti 互通时，建议 fork `POModbusMQTTCloudProvider.m` 再改，避免漏 TOTP/AES 步骤
- [ ] 强引用持有 Provider
- [ ] Debug 开 `enableMQTTLog` / `enableSDKLog` 对照日志

---

## 8. 测试建议

1. 云 MQTT 连接成功
2. 故意错 token → fetch/prepare 失败有明确 error
3. 连接成功后临时 p12 被 cleanup
4. 仅引 Core + 自定义 Cloud，不链 Adapter

---

## 9. 相关头文件

`POModbusCloudProviding.h`、`POModbusMQTTUTCInfo.h`、`POModbusMQTTTLSMaterials.h`、`POModbusSDKContext+Cloud.h`、`POModbusMQTTCloudProvider.h`
