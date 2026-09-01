package domain

import (
	"testing"
	"time"
)

func TestSession_IsExpired(t *testing.T) {
	now := time.Now()
	past := &Session{ExpiresAt: now.Add(-time.Hour)}
	future := &Session{ExpiresAt: now.Add(time.Hour)}
	if !past.IsExpired(now) {
		t.Error("past session should be expired")
	}
	if future.IsExpired(now) {
		t.Error("future session should not be expired")
	}
}

func TestDefaultHealthChecker_Probe(t *testing.T) {
	h := &DefaultHealthChecker{StaleAfter: 5 * time.Minute}

	fresh := &Machine{ID: "m1", LastHeartbeat: time.Now()}
	r, err := h.Probe(nil, fresh)
	if err != nil {
		t.Fatal(err)
	}
	if !r.OK {
		t.Error("fresh machine should be OK")
	}

	stale := &Machine{ID: "m2", LastHeartbeat: time.Now().Add(-time.Hour)}
	r, _ = h.Probe(nil, stale)
	if r.OK {
		t.Error("stale machine should NOT be OK")
	}
	if r.Message != "heartbeat-stale" {
		t.Errorf("message=%q", r.Message)
	}
}

func TestAcquireRequest_BasicShape(t *testing.T) {
	req := AcquireRequest{
		Owner:  "team-a",
		PlanID: "plan-1",
		TaskID: "task-1",
		Type:   MachineTypeHost,
		Labels: map[string]string{"region": "us-east-1"},
	}
	if req.Type != MachineTypeHost {
		t.Error("type")
	}
	if req.Labels["region"] != "us-east-1" {
		t.Error("labels")
	}
}
