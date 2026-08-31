// Package api 实现 TCM 对外的 gRPC 服务。
//
// 关联设计：[`docs/architecture-v3-modules.md §3`](../api/grpc.go)
//
// 当前状态：骨架。Sprint 1 实现 PlanService.Submit / Get / List 的真实逻辑。
package api

import (
	"github.com/aitest/tcm/internal/domain"
)

// PlanServiceServer TCM 对外暴露的 gRPC 服务。
//
// 本结构是 contracts/proto/aitest/plan/v1/plan.proto 中 PlanService 的服务端实现。
// 字段在生成代码补齐后填入：pb.UnimplementedPlanServiceServer + 实际 pb 类型。
type PlanServiceServer struct {
	// UnimplementedPlanServiceServer embed 在生成代码补齐后启用：
	// pb.UnimplementedPlanServiceServer
	Store domain.CaseStore
}

// NewPlanServiceServer 构造服务实例。
func NewPlanServiceServer(store domain.CaseStore) *PlanServiceServer {
	return &PlanServiceServer{Store: store}
}
