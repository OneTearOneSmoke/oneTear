// Package inmem 提供 CaseStore 的内存实现。
//
// 用途：开发 / 单元测试 / 烟囱测试。
// 不适用于生产环境（无持久化、无并发安全保证）。
package inmem

import (
	"context"
	"sync"

	"github.com/aitest/tcm/internal/domain"
)

// Store 内存版 CaseStore。线程安全。
type Store struct {
	mu     sync.RWMutex
	byHash map[string]*domain.Case
	byVer  map[string]*domain.Case
}

// New 构造空 Store。
func New() *Store {
	return &Store{
		byHash: make(map[string]*domain.Case),
		byVer:  make(map[string]*domain.Case),
	}
}

// Get 实现 domain.CaseStore。
func (s *Store) Get(_ context.Context, contentHash string) (*domain.Case, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c, ok := s.byHash[contentHash]
	if !ok {
		return nil, domain.ErrNotFound
	}
	return c, nil
}

// GetByVersion 实现 domain.CaseStore。
func (s *Store) GetByVersion(_ context.Context, id, semver string) (*domain.Case, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c, ok := s.byVer[id + "|" + semver]
	if !ok {
		return nil, domain.ErrNotFound
	}
	return c, nil
}

// Put 实现 domain.CaseStore。幂等。
func (s *Store) Put(_ context.Context, c *domain.Case) error {
	if err := c.Validate(); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.byHash[c.ContentHash]; exists {
		return nil
	}
	s.byHash[c.ContentHash] = c
	s.byVer[c.ID+"|"+c.Semver] = c
	return nil
}

// List 实现 domain.CaseStore（基础版本，未做 tag/lifecycle/search 过滤）。
func (s *Store) List(_ context.Context, q domain.CaseQuery) (*domain.CasePage, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*domain.Case, 0, len(s.byHash))
	for _, c := range s.byHash {
		if !matchLifecycle(c, q.Lifecycles) {
			continue
		}
		if !matchTags(c, q.Tags) {
			continue
		}
		out = append(out, c)
	}
	return &domain.CasePage{Cases: out, TotalSize: uint32(len(out))}, nil
}

// Transition 实现 domain.CaseStore。
func (s *Store) Transition(_ context.Context, id, semver string, to domain.Lifecycle) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	c, ok := s.byVer[id + "|" + semver]
	if !ok {
		return domain.ErrNotFound
	}
	if !domain.CanTransition(c.Lifecycle, to) {
		return &domain.IllegalTransition{From: c.Lifecycle, To: to}
	}
	c.Lifecycle = to
	return nil
}

// Stream 实现 domain.CaseStore。简单地把全部 case 一次性推入 chan。
func (s *Store) Stream(ctx context.Context, q domain.CaseQuery) (<-chan *domain.Case, <-chan error) {
	cases := make(chan *domain.Case, 64)
	errs := make(chan error, 1)
	go func() {
		defer close(cases)
		defer close(errs)
		page, err := s.List(ctx, q)
		if err != nil {
			errs <- err
			return
		}
		for _, c := range page.Cases {
			select {
			case <-ctx.Done():
				return
			case cases <- c:
			}
		}
	}()
	return cases, errs
}

func matchLifecycle(c *domain.Case, want []domain.Lifecycle) bool {
	if len(want) == 0 {
		return true
	}
	for _, l := range want {
		if c.Lifecycle == l {
			return true
		}
	}
	return false
}

func matchTags(c *domain.Case, q domain.TagFilter) bool {
	if len(q.AllOf) == 0 && len(q.AnyOf) == 0 && len(q.NoneOf) == 0 {
		return true
	}
	set := make(map[string]struct{}, len(c.Tags))
	for _, t := range c.Tags {
		set[t] = struct{}{}
	}
	for _, t := range q.AllOf {
		if _, ok := set[t]; !ok {
			return false
		}
	}
	if len(q.AnyOf) > 0 {
		hit := false
		for _, t := range q.AnyOf {
			if _, ok := set[t]; ok {
				hit = true
				break
			}
		}
		if !hit {
			return false
		}
	}
	for _, t := range q.NoneOf {
		if _, ok := set[t]; ok {
			return false
		}
	}
	return true
}
