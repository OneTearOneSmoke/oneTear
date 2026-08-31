package domain

import (
	"context"
	"errors"
	"time"
)

// ErrNoMatch 没有匹配机器。
var ErrNoMatch = errors.New("tmrm: no matching machine")

// ErrQuotaExceeded 配额超限。
var ErrQuotaExceeded = errors.New("tmrm: quota exceeded")

// HealthRecord 一次健康检查记录。
type HealthRecord struct {
	MachineID string
	OK        bool
	LatencyMS int64
	Message   string
	CheckedAt time.Time
}

// Allocator 机器分配器接口。
//
// 实现要点：
//   - acquire 同步 + 强一致：成功 = 机器状态 + session 两件事都落库
//   - Selector 留空即非法（避免误扫所有机器）
//   - 配额仅在 Pool 存在时生效；未配置 = 不限
type Allocator interface {
	Acquire(ctx context.Context, req AcquireRequest) (*Session, error)
	Release(ctx context.Context, sessionID string) error
	Heartbeat(ctx context.Context, machineID string) error
	HealthCheck(ctx context.Context, machineID string) (*HealthRecord, error)
	Sweep(ctx context.Context) ([]string, error) // 返回过期机器 ID
}

// HealthChecker 健康检查器接口。
type HealthChecker interface {
	Probe(ctx context.Context, m *Machine) (*HealthRecord, error)
}

// DefaultHealthChecker 默认实现：仅检查 heartbeat 是否过期。
type DefaultHealthChecker struct {
	StaleAfter time.Duration
}

// Probe 默认探针：心跳超时即视为 unhealthy。
func (h *DefaultHealthChecker) Probe(_ context.Context, m *Machine) (*HealthRecord, error) {
	stale := time.Since(m.LastHeartbeat) > h.StaleAfter
	return &HealthRecord{
		MachineID: m.ID,
		OK:        !stale,
		Message:   "heartbeat-stale",
		CheckedAt: time.Now(),
	}, nil
}
