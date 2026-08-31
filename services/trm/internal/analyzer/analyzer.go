// Package analyzer 定义 TRM 的分析器协议。
//
// 关联设计：[`docs/architecture-v3-modules.md §5`](analyzer)
package analyzer

import (
	"context"

	"github.com/aitest/trm/internal/store"
)

// Query 分析器输入。
type Query struct {
	PlanID  string
	CaseID  string
	Window  int    // 滑动窗口大小（默认 50）
	MinPct  float64 // flaky 最小失败率（默认 0.05）
	MaxPct  float64 // flaky 最大失败率（默认 0.50）
}

// Analyzer 协议。所有分析器（Flaky / Baseline / Trend）实现本接口。
type Analyzer interface {
	Name() string
	Analyze(ctx context.Context, s store.ResultStore, q Query) (Result, error)
}

// Result 分析结果（统一为键值对，由具体分析器自定义序列化）。
type Result map[string]any

// Registry 分析器注册中心。
type Registry struct {
	items map[string]Analyzer
}

// NewRegistry 构造注册中心。
func NewRegistry() *Registry {
	return &Registry{items: make(map[string]Analyzer)}
}

// Register 注册分析器。
func (r *Registry) Register(a Analyzer) {
	r.items[a.Name()] = a
}

// Get 按名字获取。
func (r *Registry) Get(name string) (Analyzer, bool) {
	a, ok := r.items[name]
	return a, ok
}

// List 全部名字。
func (r *Registry) List() []string {
	out := make([]string, 0, len(r.items))
	for k := range r.items {
		out = append(out, k)
	}
	return out
}

// FlakyDetector 滑动窗口 flaky 检测器（骨架）。
type FlakyDetector struct{}

// Name 返回 "flaky"。
func (FlakyDetector) Name() string { return "flaky" }

// Analyze 在窗口内计算失败率，处于 [MinPct, MaxPct] 视为 flaky。
//
// 当前为骨架，返回空 Result；Sprint 4 实现真实算法。
func (FlakyDetector) Analyze(_ context.Context, _ store.ResultStore, _ Query) (Result, error) {
	return Result{"status": "stub"}, nil
}

// BaselineComparator 两 run 之间的 diff（骨架）。
type BaselineComparator struct{}

// Name 返回 "baseline"。
func (BaselineComparator) Name() string { return "baseline" }

// Analyze 当前为骨架。
func (BaselineComparator) Analyze(_ context.Context, _ store.ResultStore, _ Query) (Result, error) {
	return Result{"status": "stub"}, nil
}

// TrendAnalyzer 时间线 + 长尾告警（骨架）。
type TrendAnalyzer struct{}

// Name 返回 "trend"。
func (TrendAnalyzer) Name() string { return "trend" }

// Analyze 当前为骨架。
func (TrendAnalyzer) Analyze(_ context.Context, _ store.ResultStore, _ Query) (Result, error) {
	return Result{"status": "stub"}, nil
}
