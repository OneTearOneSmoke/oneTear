module github.com/aitest/tmrm

go 1.22

require (
	github.com/aitest/contracts v0.0.0
	google.golang.org/grpc v1.65.0
)

replace github.com/aitest/contracts => ../../contracts/gen/go
