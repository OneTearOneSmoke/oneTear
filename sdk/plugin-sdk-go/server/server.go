// Package server 是 Go 插件 SDK 的核心。
//
// 关联设计：[`docs/architecture-v3-modules.md §7`](sdk)
package server

import (
	"context"
	"encoding/json"
)

// BaseServer 提供默认实现。插件作者在自己的类型里嵌入 BaseServer，然后
// 通过 RegisterCommand / RegisterAssertor 注册命令与断言器。
//
// Sprint 1 接入真实 gRPC handler 与 Manifest 上报。
type BaseServer struct {
	Name      string
	Version   string
	commands  map[string]CommandHandler
	assertors map[string]AssertorHandler
}

// CommandHandler 命令处理器签名。
//
// 参数 args 为 JSON RawMessage；返回 output 同样为 JSON RawMessage。
// 错误由 SDK 序列化为 InvokeResponse(status=FAILED/ERROR)。
type CommandHandler func(ctx context.Context, args json.RawMessage) (json.RawMessage, error)

// AssertorHandler 断言器签名。
type AssertorHandler func(ctx context.Context, value, spec json.RawMessage) (AssertResult, error)

// AssertResult 断言结果。
type AssertResult struct {
	Passed      bool                `json:"passed"`
	Message     string              `json:"message,omitempty"`
	Diagnostics map[string]any      `json:"diagnostics,omitempty"`
}

// NewBaseServer 构造基础 server。name/version 在 Manifest 上报。
func NewBaseServer(name, version string) *BaseServer {
	return &BaseServer{
		Name:      name,
		Version:   version,
		commands:  make(map[string]CommandHandler),
		assertors: make(map[string]AssertorHandler),
	}
}

// RegisterCommand 注册命令。
func (b *BaseServer) RegisterCommand(name string, h CommandHandler) {
	b.commands[name] = h
}

// RegisterAssertor 注册断言器。
func (b *BaseServer) RegisterAssertor(name string, h AssertorHandler) {
	b.assertors[name] = h
}

// Commands 返回已注册命令列表（骨架用，真实 gRPC 在 Sprint 1）。
func (b *BaseServer) Commands() map[string]CommandHandler {
	return b.commands
}

// Assertors 返回已注册断言器列表。
func (b *BaseServer) Assertors() map[string]AssertorHandler {
	return b.assertors
}

// Serve 启动 gRPC server。addr 例如 ":50051"。
//
// 骨架实现：仅打印注册表。Sprint 1 接入真实 tonic / grpc-go server。
func (b *BaseServer) Serve(addr string) error {
	// TODO S1: grpc.NewServer() → RegisterPluginServiceServer() → Serve(addr)
	_ = addr
	return nil
}
