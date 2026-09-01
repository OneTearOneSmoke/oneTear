package analyzer

import (
	"context"
	"testing"
)

func TestRegistry_RegisterAndGet(t *testing.T) {
	r := NewRegistry()
	r.Register(FlakyDetector{})
	r.Register(BaselineComparator{})

	if a, ok := r.Get("flaky"); !ok || a.Name() != "flaky" {
		t.Errorf("get flaky failed: ok=%v", ok)
	}
	if _, ok := r.Get("nope"); ok {
		t.Error("expected miss for unknown name")
	}
}

func TestRegistry_List(t *testing.T) {
	r := NewRegistry()
	r.Register(FlakyDetector{})
	r.Register(BaselineComparator{})
	r.Register(TrendAnalyzer{})
	names := r.List()
	if len(names) != 3 {
		t.Errorf("list len=%d, want 3", len(names))
	}
}

func TestFlakyDetector_NameAndStub(t *testing.T) {
	a := FlakyDetector{}
	if a.Name() != "flaky" {
		t.Errorf("name=%s", a.Name())
	}
	r, err := a.Analyze(context.Background(), nil, Query{})
	if err != nil {
		t.Fatal(err)
	}
	if r["status"] != "stub" {
		t.Errorf("got %v", r)
	}
}
