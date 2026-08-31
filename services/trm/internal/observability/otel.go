// Package observability TRM 的 OTel 接入模板（骨架）。
package observability

import "context"

type Shutdown func(context.Context) error

func Setup(_ string, _ string) (Shutdown, error) {
	return func(context.Context) error { return nil }, nil
}
