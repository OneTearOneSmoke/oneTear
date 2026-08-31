// Package domain 定义 TMRM 的领域类型。
//
// 关联设计：[`docs/architecture-v3-modules.md §6`](machine.go)
package domain

import "time"

// MachineType 机器类型。
type MachineType string

const (
	MachineTypeHost     MachineType = "host"
	MachineTypeBrowser  MachineType = "browser"
	MachineTypeMobile   MachineType = "mobile"
	MachineTypeDesktop  MachineType = "desktop"
	MachineTypeSandbox  MachineType = "sandbox"
)

// MachineStatus 机器状态。
type MachineStatus string

const (
	StatusAvailable  MachineStatus = "available"
	StatusAllocated  MachineStatus = "allocated"
	StatusDrained    MachineStatus = "drained"
	StatusRetired    MachineStatus = "retired"
)

// Machine 机器注册条目。
type Machine struct {
	ID            string
	Name          string
	Type          MachineType
	Pool          string
	Provider      string // "aws" / "gcp" / "azure" / "bare-metal"
	Region        string
	Status        MachineStatus
	Labels        map[string]string
	Capacity      int // 并发 slot 数
	LastHeartbeat time.Time
	CreatedAt     time.Time
}

// Pool 机器池。
type Pool struct {
	ID       string
	Name     string
	Provider string
	Region   string
	Selector map[string]string // 默认选择器
	Quota    map[string]int    // team → max_sessions
}

// Session 一个 EXF run 占用记录。
type Session struct {
	ID         string
	MachineID  string
	Owner      string // team / user
	PlanID     string
	TaskID     string
	AcquiredAt time.Time
	ExpiresAt  time.Time
	Labels     map[string]string
}

// IsExpired 是否已过期。
func (s *Session) IsExpired(now time.Time) bool {
	return now.After(s.ExpiresAt)
}

// AcquireRequest 分配请求。
type AcquireRequest struct {
	Owner   string
	PlanID  string
	TaskID  string
	Type    MachineType
	Pool    string
	Labels  map[string]string
	TTL     time.Duration
}
