// Package domain 定义 TCM 的领域类型与核心接口。
//
// 与 contracts/proto 的关系：
//   - contracts/proto 定义传输 / wire 格式
//   - 本包定义"语义化"领域类型（用 Go 内置类型而非 proto message）
//   - api 层负责两者之间转换
package domain

import (
	"context"
	"encoding/json"
	"errors"
	"time"
)

// Lifecycle 用例生命周期。
//
// 转移规则（详见 docs/architecture-v3-modules.md §3）：
//
//	Draft       → Active | Retired
//	Active      → Deprecated | Retired
//	Deprecated  → Active | Retired
//	Retired     → (终态)
type Lifecycle int

const (
	LifecycleUnspecified Lifecycle = iota
	LifecycleDraft
	LifecycleActive
	LifecycleDeprecated
	LifecycleRetired
)

func (l Lifecycle) String() string {
	switch l {
	case LifecycleDraft:
		return "draft"
	case LifecycleActive:
		return "active"
	case LifecycleDeprecated:
		return "deprecated"
	case LifecycleRetired:
		return "retired"
	}
	return "unspecified"
}

// IllegalTransition 非法状态转移错误。
type IllegalTransition struct {
	From, To Lifecycle
}

func (e *IllegalTransition) Error() string {
	return "illegal lifecycle transition: " + e.From.String() + " -> " + e.To.String()
}

// CanTransition 返回 from → to 是否合法。
func CanTransition(from, to Lifecycle) bool {
	switch from {
	case LifecycleDraft:
		return to == LifecycleActive || to == LifecycleRetired
	case LifecycleActive:
		return to == LifecycleDeprecated || to == LifecycleRetired
	case LifecycleDeprecated:
		return to == LifecycleActive || to == LifecycleRetired
	case LifecycleRetired:
		return false
	}
	return false
}

// Case 一条用例的不可变快照。
//
// 唯一性：(ContentHash, Semver) 或 (ID, Semver)。
// ContentHash 由规范化字段计算（剔除 Path / CreatedAt / UpdatedAt）。
type Case struct {
	ContentHash string          `json:"content_hash"`
	Semver      string          `json:"semver"`
	ID          string          `json:"id"`
	Name        string          `json:"name"`
	Description string          `json:"description,omitempty"`
	Tags        []string        `json:"tags"`
	Lifecycle   Lifecycle       `json:"lifecycle"`
	Params      json.RawMessage `json:"params,omitempty"`
	Steps       []Step          `json:"steps"`
	Author      Author          `json:"author"`
	CreatedAt   time.Time       `json:"created_at"`
	UpdatedAt   time.Time       `json:"updated_at"`
}

// Step 一个执行步骤。
type Step struct {
	Name              string          `json:"name"`
	Plugin            string          `json:"plugin"`
	Action            string          `json:"action"`
	Args              json.RawMessage `json:"args,omitempty"`
	TimeoutMS         int64          `json:"timeout_ms,omitempty"`
	ContinueOnFailure bool            `json:"continue_on_failure,omitempty"`
}

// Author 作者信息。
type Author struct {
	Name       string `json:"name"`
	Email      string `json:"email,omitempty"`
	AIAssisted bool   `json:"ai_assisted,omitempty"`
	Model      string `json:"model,omitempty"`
}

// IsExecutable lifecycle 是否允许被 EXF 执行。
func (c *Case) IsExecutable() bool {
	return c.Lifecycle == LifecycleActive || c.Lifecycle == LifecycleDeprecated
}

// Validate 校验 Case 字段完整性。
func (c *Case) Validate() error {
	if c.ID == "" {
		return errors.New("case: id is required")
	}
	if c.ContentHash == "" {
		return errors.New("case: content_hash is required")
	}
	if c.Semver == "" {
		return errors.New("case: semver is required")
	}
	if len(c.Steps) == 0 {
		return errors.New("case: steps is required")
	}
	return nil
}
