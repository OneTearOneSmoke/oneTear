//! EXF 服务入口（Sprint 1 骨架）
//!
//! 当前只做：
//!   1. 构造 InMemoryScheduler + InMemoryBroker
//!   2. 暴露一个 PlanService gRPC server（端口可由 --addr 配置，默认 :7102）
//!   3. 优雅停机信号处理
//!
//! 真实 gRPC + 调度主循环在 Sprint 1 接入。

use std::sync::Arc;

use aitest_broker::InMemoryBroker;
use aitest_scheduler::{InMemoryScheduler, Scheduler};
use tokio_util::sync::CancellationToken;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = std::env::args()
        .collect::<Vec<_>>()
        .iter()
        .position(|a| a == "--addr")
        .and_then(|i| std::env::args().nth(i + 1))
        .unwrap_or_else(|| ":7102".to_string());

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    let scheduler = Arc::new(InMemoryScheduler::new());
    let broker: Arc<dyn aitest_broker::Broker> = Arc::new(InMemoryBroker::new());

    tracing::info!(%addr, "exf-server starting (skeleton)");
    tracing::info!("scheduler ready; broker ready; no gRPC handlers wired yet (Sprint 1)");

    // 烟囱测试：submit + status
    use aitest_scheduler::TaskSpec;
    let specs = vec![TaskSpec {
        case_id: "smoke.hello".into(),
        content_hash: "deadbeef".into(),
        semver: "1.0.0".into(),
        params: serde_json::json!({}),
        priority: 0,
    }];
    let h = scheduler.submit("plan-smoke", &specs, CancellationToken::new()).await?;
    let s = scheduler.status("plan-smoke").await?;
    tracing::info!(plan_id = %h.plan_id, queued = s.queued, "smoke test ok");

    let _ = broker; // 等待 Sprint 3 接入

    // 占位：等到 Ctrl-C
    tokio::signal::ctrl_c().await?;
    tracing::info!("exf-server shutting down");
    Ok(())
}
