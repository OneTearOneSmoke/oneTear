package domain

import (
	"context"
	"errors"
)

// ErrNotFound 通用未找到错误。
var ErrNotFound = errors.New("domain: not found")

// ErrAlreadyExists 重复写入错误（按 content_hash 判定）。
var ErrAlreadyExists = errors.New("domain: already exists")

// CaseQuery 用例查询条件。
//
// 与 contracts.proto 的 CaseSelector 对应但更精简：
//   - 协议层支持 oneof refs/tag_query/suite/pin
//   - 这里统一为结构化字段 + Search 字符串
type CaseQuery struct {
	Tags        TagFilter // 多维 tag 过滤
	Lifecycles  []Lifecycle
	SemverRange string
	Search      string // 全文检索关键词
	Limit       int    // <= 0 表示不限
	Cursor      string // 分页游标
}

// TagFilter 多维 tag 过滤。AND / OR / NOT 组合。
type TagFilter struct {
	AllOf  []string // 必须全部命中
	AnyOf  []string // 命中任一
	NoneOf []string // 必须全部不命中
}

// CasePage 分页结果。
type CasePage struct {
	Cases         []*Case
	NextPageToken string
	TotalSize     uint32
}

// CaseStore 用例存储接口。
//
// 设计要点：
//   - 4 类 Adapter：Postgres（生产）/ InMemory（开发测试）/ Search（ES/OpenSearch）/ Cas（资产）
//   - Stream 返回 chan 用于 EXF 展开 ResolvedCaseRef（避免一次性加载百万级用例）
//   - 写接口幂等：相同 content_hash 写入不报错（视为同一 immutable 快照）
//
// 关联设计：[`docs/architecture-v3-modules.md §3` CaseStore](
type CaseStore interface {
	// Get 按 content_hash 读取。
	Get(ctx context.Context, contentHash string) (*Case, error)

	// GetByVersion 按 (id, semver) 读取。
	GetByVersion(ctx context.Context, id, semver string) (*Case, error)

	// Put 写入或更新。
	//
	// 幂等：相同 ContentHash 已存在时不报错。
	// 错误：若 lifecycle 非法转移，返回 *IllegalTransition。
	Put(ctx context.Context, c *Case) error

	// List 分页查询。
	List(ctx context.Context, q CaseQuery) (*CasePage, error)

	// Transition 强制 lifecycle 转移。
	//
	// 错误：非法转移返回 *IllegalTransition；不存在返回 ErrNotFound。
	Transition(ctx context.Context, id, semver string, to Lifecycle) error

	// Stream 流式读取（用于 EXF Plan 展开）。
	//
	// 调用方必须消费 Cases chan 与 Errs chan，并在 Done 后 Close。
	Stream(ctx context.Context, q CaseQuery) (<-chan *Case, <-chan error)
}

// EventPublisher 事件发布接口（TCM 内部 → NATS / Kafka）。
//
// 用于跨服务通知：
//   - CaseCreated / CaseUpdated / CaseTransitioned
//   - PlanSubmitted（与 EXF 联动）
type EventPublisher interface {
	Publish(ctx context.Context, topic string, key string, payload []byte) error
	Close() error
}
