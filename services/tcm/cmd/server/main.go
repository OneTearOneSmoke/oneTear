// TCM 服务入口（Sprint 1 骨架）。
//
// 当前只做：
//   1. 初始化可观测
//   2. 构造内存版 CaseStore
//   3. 暴露 gRPC server（端口可由 --addr 配置，默认 :7101）
//
// 真实 gRPC handler 在 Sprint 1 接入。
package main

import (
	"context"
	"flag"
	"log"

	"github.com/aitest/tcm/internal/domain"
	"github.com/aitest/tcm/internal/observability"
	"github.com/aitest/tcm/internal/store/inmem"
)

func main() {
	addr := flag.String("addr", ":7101", "gRPC listen address")
	flag.Parse()

	shutdown, err := observability.Setup("tcm", "v0.1.0")
	if err != nil {
		log.Fatalf("observability setup failed: %v", err)
	}
	defer func() {
		_ = shutdown(context.Background())
	}()

	var store domain.CaseStore = inmem.New()
	_ = store // TODO S1: 接到 gRPC handler

	log.Printf("tcm: starting on %s (inmem store)", *addr)
	log.Printf("tcm: ready (stub; real gRPC in Sprint 1)")
	// TODO S1: grpc.NewServer → RegisterPlanServiceServer → Serve(*addr)
	select {}
}
