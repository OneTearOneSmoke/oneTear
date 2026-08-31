# PLG SDK —— 插件协议多语言 SDK

> 目标：插件作者只需 1. 注册命令处理器；2. 实现业务逻辑；3. 调用 `serve()`。
> SDK 自动接管 gRPC、Health、Trace、Cancel、Codec。

关联设计：[`docs/architecture-v3-modules.md §7`](../../docs/architecture-v3-modules.md)
协议：[`contracts/proto/aitest/plugin/v1/plugin.proto`](../../contracts/proto/aitest/plugin/v1/plugin.proto)

## SDK 矩阵

| 语言 | 路径 | 状态 | 备注 |
| --- | --- | --- | --- |
| Go | `plugin-sdk-go/` | 骨架 | 后续 Sprint 5 完善 |
| Rust | `plugin-sdk-rust/` | 骨架 | 后续 Sprint 5 完善 |
| Python | `plugin-sdk-python/` | 骨架 | 后续 Sprint 5 完善 |
| Java | `plugin-sdk-java/` | TODO | Sprint 5 起 |

## 各 SDK 的最小示例

### Go

```go
package main

import (
    "context"
    sdk "github.com/aitest/sdk-go/server"
)

type SorterPlugin struct{ sdk.BaseServer }

func (p *SorterPlugin) Commands() []sdk.CommandSpec {
    return []sdk.CommandSpec{{Name: "sort", Description: "sort ints"}}
}

func (p *SorterPlugin) Invoke(ctx context.Context, name string, args json.RawMessage) (json.RawMessage, error) {
    var in []int
    json.Unmarshal(args, &in)
    sort.Ints(in)
    return json.Marshal(in)
}

func main() { (&SorterPlugin{}).Serve(":50051") }
```

### Python

```python
from aitest_sdk import PluginServer

server = PluginServer(name="sort", version="0.1.0")

@server.command("sort")
def sort_ints(args):
    data = args["input"]
    return {"sorted": sorted(data)}

server.serve()
```
