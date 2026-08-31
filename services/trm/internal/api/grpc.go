// Package api 实现 TRM 对外的 gRPC 服务。
package api

import (
	"github.com/aitest/trm/internal/analyzer"
	"github.com/aitest/trm/internal/store"
)

// ResultServiceServer TRM 对外暴露的 gRPC 服务。
type ResultServiceServer struct {
	// UnimplementedResultServiceServer 在生成代码补齐后启用
	Store     store.ResultStore
	Analyzers *analyzer.Registry
}

// NewResultServiceServer 构造服务实例。
func NewResultServiceServer(s store.ResultStore, r *analyzer.Registry) *ResultServiceServer {
	return &ResultServiceServer{Store: s, Analyzers: r}
}
