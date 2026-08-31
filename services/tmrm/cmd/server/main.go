// TMRM 服务入口（Sprint 1 骨架）。
package main

import (
	"flag"
	"log"

	"github.com/aitest/tmrm/internal/observability"
)

func main() {
	addr := flag.String("addr", ":7104", "gRPC listen address")
	flag.Parse()

	shutdown, err := observability.Setup("tmrm", "v0.1.0")
	if err != nil {
		log.Fatalf("observability setup failed: %v", err)
	}
	defer func() { _ = shutdown(shutdownCtx()) }()

	log.Printf("tmrm: starting on %s (skeleton)", *addr)
	log.Printf("tmrm: ready")
	select {}
}

func shutdownCtx() context.Context { return context.Background() }
