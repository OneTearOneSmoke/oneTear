package server

import (
	"context"
	"encoding/json"
	"testing"
)

func TestBaseServer_RegisterCommand(t *testing.T) {
	s := NewBaseServer("sort", "0.1.0")
	s.RegisterCommand("sort", func(_ context.Context, args json.RawMessage) (json.RawMessage, error) {
		var in []int
		_ = json.Unmarshal(args, &in)
		for i := 0; i < len(in)/2; i++ {
			in[i], in[len(in)-1-i] = in[len(in)-1-i], in[i]
		}
		return json.Marshal(in)
	})
	if len(s.Commands()) != 1 {
		t.Fatalf("expected 1 command, got %d", len(s.Commands()))
	}
}
