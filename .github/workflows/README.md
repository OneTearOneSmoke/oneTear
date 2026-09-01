# CI Workflows

> 4 个独立的 GitHub Actions workflow，每个关注一个测试链。
> 它们之间通过 **artifact 共享**生成的 proto 代码（`contracts-gen-go`）。

## Workflow 列表

| Workflow | 触发 | 内容 | 入口文件 |
| --- | --- | --- | --- |
| `contracts` | `contracts/**` | buf lint + buf format + buf breaking + Go 生成烟囱 | `contracts.yml` |
| `rust` | `services/exf/**` + `sdk/plugin-sdk-rust/**` | cargo fmt + check + test + clippy (advisory) | `rust.yml` |
| `go` | `services/**` + `sdk/plugin-sdk-go/**` + `contracts/**` | buf generate + go vet/build/test | `go.yml` |
| `python` | `sdk/plugin-sdk-python/**` | pytest 多版本矩阵 + import 烟囱 | `python.yml` |

## CI 状态（最近一次）

| Workflow | 状态 | 备注 |
| --- | --- | --- |
| `python` | ✅ success | 6/6 pytest 通过 |
| `rust` | ⚠️ 部分失败 | fmt/test/clippy 失败；待代码侧修复 |
| `contracts` | ⚠️ 配置错误 | 已修：用 `buf-action-setup@v1` 替代错误的 `buf-action@v1` 输入 |
| `go` | ⚠️ 配置错误 | 同上 |

## 历史教训

- ❌ `bufbuild/buf-action@v1` 的 `version` input 是错的；正确 input 是 `buf_version`，且 v1 已 split 为 `buf-action` 与 `buf-action-setup@v1`
- ✅ 用 `bufbuild/buf-action-setup@v1` + 手动 `buf ...` 是最稳的写法
- ✅ `cargo clippy -D warnings` 太严：先 advisory（continue-on-error）让真实问题浮出水面，再决定是否升级为 blocking

## 矩阵

| 维度 | 默认值 |
| --- | --- |
| Go | 1.22 |
| Rust | stable |
| Python | 3.10 / 3.11 / 3.12 (matrix) |
| 触发 | push to main / new_frame；PR to main |

## 跨 workflow 依赖

`go.yml` 中的 `buf-generate` job 把生成的 proto 代码上传为 artifact，下游
`tcm / trm / tmrm / plugin-sdk-go` jobs 通过 `actions/download-artifact`
获取，避免重复生成。

## 本地复现

```bash
make ci            # 全跑
make ci-contracts  # 仅 buf
make ci-rust       # 仅 Rust
make ci-go         # 仅 Go
make ci-python     # 仅 Python
```
