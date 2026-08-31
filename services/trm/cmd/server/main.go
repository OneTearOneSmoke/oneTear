// TRM 服务入口（Sprint 1 骨架）。
package main

import (
	"context"
	"flag"
	"log"

	"github.com/aitest/trm/internal/analyzer"
	"github.com/aitest/trm/internal/observability"
)

func main() {
	addr := flag.String("addr", ":7103", "gRPC listen address")
	flag.Parse()

	shutdown, err := observability.Setup("trm", "v0.1.0")
	if err != nil {
		log.Fatalf("observability setup failed: %v", err)
	}
	defer func() { _ = shutdown(context.Background()) }()

	reg := analyzer.NewRegistry()
	reg.Register(analyzer.FlakyDetector{})
	reg.Register(analyzer.BaselineComparator{})
	reg.Register(analyzer.TrendAnalyzer{})

	log.Printf("trm: starting on %s (inmem)", *addr)
	log.Printf("trm: analyzers registered: %v", reg.List())
	log.Printf("trm: ready (stub)")
	select {}
}
