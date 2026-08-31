// Package observability 提供 TCM 的 OTel 接入模板。
//
// 关联设计：[`docs/architecture-v3-modules.md §9.1`](../api/grpc.go)
//
// 当前状态：骨架。Sprint 2 接入真实 OTel exporter。
package observability

import (
	"context"
)

// Shutdown 可观测资源关闭。
type Shutdown func(context.Context) error

// Setup 初始化 Tracer / Meter / Logger。
//
// 返回 Shutdown，main 中 defer 调用。
//
// 当前为骨架：返回空 Shutdown，便于代码通过编译。
func Setup(_ string, _ string) (Shutdown, error) {
	return func(context.Context) error { return nil }, nil
}
