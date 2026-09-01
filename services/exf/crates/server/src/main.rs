//! EXF 服务入口（Sprint 1）
//!
//! 当前状态：
//!   1. 构造 InMemoryScheduler + InMemoryBroker
//!   2. 暴露 PlanService trait（gRPC handler trait，由 grpc.rs 定义）
//!   3. 优雅停机信号处理
//!
//! Sprint 1 后续：接入 tonic + plan.proto codegen + WorkerPool 主循环。
//! Sprint 3：替换 InMemoryBroker 为 NATS JetStream。

pub mod grpc;

use std::sync::Arc;

use aitest_broker::InMemoryBroker;
use aitest_scheduler::{InMemoryScheduler, Scheduler};
use tokio_util::sync::CancellationToken;
use tracing_subscriber::EnvFilter;

use crate::grpc::{PlanService, SchedulerBackedPlanService};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = std::env::args()
        .collect::<Vec<_>>()
        .iter()
        .position(|a| a == "--addr")
        .and_then(|i| std::env::args().nth(i + 1))
        .unwrap_or_else(|| ":7102".to_string());

    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let scheduler = Arc::new(InMemoryScheduler::new());
    let broker: Arc<dyn aitest_broker::Broker> = Arc::new(InMemoryBroker::new());
    let plan_service: Arc<dyn PlanService> = Arc::new(SchedulerBackedPlanService::new(scheduler.clone()));

    tracing::info!(%addr, "exf-server starting (Sprint 1)");
    tracing::info!("scheduler ready; broker ready; PlanService trait wired; tonic pending");

    // 烟囱测试：submit + status + cancel
    use crate::grpc::{ResolvedCaseRef, SubmitPlanInput};
    let input = SubmitPlanInput {
        plan_id: "plan-smoke".into(),
        idempotency_key: None,
        validate_only: false,
        specs: vec![ResolvedCaseRef {
            case_id: "smoke.hello".into(),
            content_hash: "deadbeef".into(),
            semver: "1.0.0".into(),
            params: serde_json::json!({}),
            depends_on: vec![],
            priority: 0,
            max_attempts: 3,
        }],
    };
    let out = plan_service.submit(input, CancellationToken::new()).await?;
    tracing::info!(
        plan_id = %out.plan_id,
        accepted = out.accepted,
        task_count = out.resolved_case_count,
        "smoke: submit ok"
    );

    let st = plan_service.get("plan-smoke").await?;
    tracing::info!(queued = st.queued, running = st.running, "smoke: status ok");

    let cancel = plan_service.cancel("plan-smoke", "smoke-test", false).await?;
    tracing::info!(cancelled = cancel.cancelled_tasks, "smoke: cancel ok");

    let _ = broker; // 等待 Sprint 3 接入

    // 占位：等到 Ctrl-C
    tokio::signal::ctrl_c().await?;
    tracing::info!("exf-server shutting down");
    Ok(())
}
