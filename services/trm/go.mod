module github.com/aitest/trm

go 1.22

require (
	github.com/aitest/contracts v0.0.0
	google.golang.org/grpc v1.65.0
	google.golang.org/protobuf v1.34.2
)

replace github.com/aitest/contracts => ../../contracts/gen/go
