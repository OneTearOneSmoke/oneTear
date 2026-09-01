package domain

import (
	"encoding/json"
	"testing"
)

func TestCanTransition(t *testing.T) {
	cases := []struct {
		name string
		from Lifecycle
		to   Lifecycle
		want bool
	}{
		{"draft→active", LifecycleDraft, LifecycleActive, true},
		{"draft→retired", LifecycleDraft, LifecycleRetired, true},
		{"draft→deprecated", LifecycleDraft, LifecycleDeprecated, false},
		{"active→deprecated", LifecycleActive, LifecycleDeprecated, true},
		{"active→retired", LifecycleActive, LifecycleRetired, true},
		{"active→draft", LifecycleActive, LifecycleDraft, false},
		{"deprecated→active", LifecycleDeprecated, LifecycleActive, true},
		{"deprecated→retired", LifecycleDeprecated, LifecycleRetired, true},
		{"retired→*", LifecycleRetired, LifecycleActive, false},
		{"retired→retired", LifecycleRetired, LifecycleRetired, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := CanTransition(tc.from, tc.to)
			if got != tc.want {
				t.Errorf("CanTransition(%s, %s)=%v, want %v", tc.from, tc.to, got, tc.want)
			}
		})
	}
}

func TestCase_IsExecutable(t *testing.T) {
	draft := &Case{Lifecycle: LifecycleDraft}
	active := &Case{Lifecycle: LifecycleActive}
	deprecated := &Case{Lifecycle: LifecycleDeprecated}
	retired := &Case{Lifecycle: LifecycleRetired}
	if draft.IsExecutable() {
		t.Error("draft should not be executable")
	}
	if !active.IsExecutable() {
		t.Error("active should be executable")
	}
	if !deprecated.IsExecutable() {
		t.Error("deprecated should still be executable")
	}
	if retired.IsExecutable() {
		t.Error("retired should not be executable")
	}
}

func TestCase_Validate(t *testing.T) {
	bad := &Case{}
	if err := bad.Validate(); err == nil {
		t.Error("expected error for empty case")
	}
	good := &Case{
		ContentHash: "h",
		Semver:      "1.0.0",
		ID:          "x",
		Steps:       []Step{{Name: "s"}},
		Params:      json.RawMessage(`{}`),
	}
	if err := good.Validate(); err != nil {
		t.Errorf("good case: %v", err)
	}
}

func TestLifecycle_String(t *testing.T) {
	if LifecycleDraft.String() != "draft" {
		t.Error("draft string mismatch")
	}
	if LifecycleUnspecified.String() != "unspecified" {
		t.Error("unspecified string mismatch")
	}
}
