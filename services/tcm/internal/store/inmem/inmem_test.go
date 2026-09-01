package inmem

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/aitest/tcm/internal/domain"
)

func mkCase(id, hash, semver string, tags ...string) *domain.Case {
	return &domain.Case{
		ContentHash: hash,
		Semver:      semver,
		ID:          id,
		Name:        id,
		Tags:        tags,
		Lifecycle:   domain.LifecycleActive,
		Params:      json.RawMessage(`{}`),
		Steps:       []domain.Step{{Name: "s1", Plugin: "p", Action: "a"}},
	}
}

func TestStore_PutGet(t *testing.T) {
	ctx := context.Background()
	s := New()
	c := mkCase("ai.sort", "h1", "1.0.0", "smoke")
	if err := s.Put(ctx, c); err != nil {
		t.Fatalf("put: %v", err)
	}
	got, err := s.Get(ctx, "h1")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if got.ID != "ai.sort" {
		t.Errorf("got id=%q", got.ID)
	}
	got2, err := s.GetByVersion(ctx, "ai.sort", "1.0.0")
	if err != nil {
		t.Fatalf("getbyversion: %v", err)
	}
	if got2.ContentHash != "h1" {
		t.Errorf("got hash=%q", got2.ContentHash)
	}
}

func TestStore_PutIdempotent(t *testing.T) {
	ctx := context.Background()
	s := New()
	c := mkCase("x", "h", "1")
	if err := s.Put(ctx, c); err != nil {
		t.Fatalf("put1: %v", err)
	}
	// Same hash → idempotent no-op
	if err := s.Put(ctx, c); err != nil {
		t.Fatalf("put2: %v", err)
	}
	page, err := s.List(ctx, domain.CaseQuery{})
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if page.TotalSize != 1 {
		t.Errorf("total=%d, want 1", page.TotalSize)
	}
}

func TestStore_PutRejectsInvalid(t *testing.T) {
	ctx := context.Background()
	s := New()
	bad := &domain.Case{ID: "x"} // missing content_hash / semver / steps
	if err := s.Put(ctx, bad); err == nil {
		t.Fatal("expected validation error")
	}
}

func TestStore_GetMissing(t *testing.T) {
	ctx := context.Background()
	s := New()
	_, err := s.Get(ctx, "nope")
	if !errors.Is(err, domain.ErrNotFound) {
		t.Errorf("err=%v, want ErrNotFound", err)
	}
}

func TestStore_Transition(t *testing.T) {
	ctx := context.Background()
	s := New()
	c := mkCase("x", "h", "1")
	_ = s.Put(ctx, c)

	if err := s.Transition(ctx, "x", "1", domain.LifecycleDeprecated); err != nil {
		t.Fatalf("transition: %v", err)
	}
	got, _ := s.GetByVersion(ctx, "x", "1")
	if got.Lifecycle != domain.LifecycleDeprecated {
		t.Errorf("got %s, want deprecated", got.Lifecycle)
	}

	// Illegal: deprecated → draft
	if err := s.Transition(ctx, "x", "1", domain.LifecycleDraft); err == nil {
		t.Error("expected illegal transition error")
	}
}

func TestStore_List_TagFilter(t *testing.T) {
	ctx := context.Background()
	s := New()
	_ = s.Put(ctx, mkCase("a", "h1", "1", "smoke", "ai"))
	_ = s.Put(ctx, mkCase("b", "h2", "1", "smoke"))
	_ = s.Put(ctx, mkCase("c", "h3", "1", "perf"))

	// AllOf = smoke
	page, err := s.List(ctx, domain.CaseQuery{Tags: domain.TagFilter{AllOf: []string{"smoke"}}})
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if page.TotalSize != 2 {
		t.Errorf("smoke total=%d, want 2", page.TotalSize)
	}

	// AnyOf = ai|perf
	page, _ = s.List(ctx, domain.CaseQuery{Tags: domain.TagFilter{AnyOf: []string{"ai", "perf"}}})
	if page.TotalSize != 2 {
		t.Errorf("ai|perf total=%d, want 2", page.TotalSize)
	}

	// AllOf smoke + NoneOf perf
	page, _ = s.List(ctx, domain.CaseQuery{Tags: domain.TagFilter{AllOf: []string{"smoke"}, NoneOf: []string{"perf"}}})
	if page.TotalSize != 1 || page.Cases[0].ID != "a" {
		t.Errorf("smoke-not-perf: got %+v", page.Cases)
	}
}

func TestStore_List_LifecycleFilter(t *testing.T) {
	ctx := context.Background()
	s := New()
	a := mkCase("a", "h1", "1")
	b := mkCase("b", "h2", "1")
	_ = s.Put(ctx, a)
	_ = s.Put(ctx, b)
	_ = s.Transition(ctx, "b", "1", domain.LifecycleDeprecated)

	page, _ := s.List(ctx, domain.CaseQuery{Lifecycles: []domain.Lifecycle{domain.LifecycleActive}})
	if page.TotalSize != 1 || page.Cases[0].ID != "a" {
		t.Errorf("active-only: got %+v", page.Cases)
	}
}

func TestStore_Stream(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	s := New()
	for i := 0; i < 5; i++ {
		_ = s.Put(ctx, mkCase(
			"c"+string(rune('a'+i)),
			"h"+string(rune('a'+i)),
			"1",
		))
	}
	casesCh, errs := s.Stream(ctx, domain.CaseQuery{})
	count := 0
	for c := range casesCh {
		_ = c
		count++
	}
	if count != 5 {
		t.Errorf("streamed %d, want 5", count)
	}
	if err := <-errs; err != nil {
		t.Errorf("errs: %v", err)
	}
}
