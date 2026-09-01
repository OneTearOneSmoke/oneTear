# CI Workflows

> 4 个独立的 GitHub Actions workflow，每个关注一个测试链。
> 它们之间通过 **artifact 共享**生成的 proto 代码（`contracts-gen-go`）。

## Workflow 列表

| Workflow | 触发 | 内容 | 入口文件 |
| --- | --- | --- | --- |
| `contracts` | `contracts/**` | buf lint + buf format + buf breaking + Go 生成烟囱 | `contracts.yml` |
| `rust` | `services/exf/**` + `sdk/plugin-sdk-rust/**` | cargo fmt + clippy + test | `rust.yml` |
| `go` | `services/**` + `sdk/plugin-sdk-go/**` + `contracts/**` | buf generate + go vet/build/test | `go.yml` |
| `python` | `sdk/plugin-sdk-python/**` | pytest 多版本矩阵 + import 烟囱 | `python.yml` |

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
