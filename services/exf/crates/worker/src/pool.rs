//! WorkerPool —— EXF 数据面（执行面）
//!
//! 设计意图：
//! - 一个 WorkerPool = 一组并发执行 Task 的 worker 协程
//! - 池池可向 Broker 订阅 topic、拉取 Task、调用插件、回写结果
//! - 池池大小可动态调整（背压信号驱动）
//!
//! 与 core/worker 的关系：
//! - `lib.rs` 的 Worker trait = 单个 worker 的语义抽象
//! - 本模块的 WorkerPool = worker 集合管理

use std::sync::Arc;
use std::time::Duration;

use aitest_broker::{Broker, BrokerError};
use aitest_core::Task;
use async_trait::async_trait;
use thiserror::Error;
use tokio_util::sync::CancellationToken;

/// 池池配置
#[derive(Debug, Clone)]
pub struct PoolConfig {
    /// 工作协程数（最大并发 Task 数）
    pub concurrency: u32,
    /// 单个 Task 的默认超时（来自 plan / case 时可覆盖）
    pub default_task_timeout: Duration,
    /// 优雅停机最大等待时长
    pub shutdown_grace: Duration,
    /// Broker topic 名称
    pub topic: String,
}

impl Default for PoolConfig {
    fn default() -> Self {
        Self {
            concurrency: 32,
            default_task_timeout: Duration::from_secs(60),
            shutdown_grace: Duration::from_secs(10),
            topic: "exf.tasks".to_string(),
        }
    }
}

/// 池池运行时统计
#[derive(Debug, Clone, Default)]
pub struct PoolStats {
    pub running: u32,
    pub queued: u32,
    pub succeeded_total: u64,
    pub failed_total: u64,
    pub last_activity_ms: u64,
}

/// 池池错误
#[derive(Debug, Error)]
pub enum PoolError {
    #[error("broker: {0}")]
    Broker(#[from] BrokerError),
    #[error("plugin call: {0}")]
    Plugin(String),
    #[error("timeout after {0:?}")]
    Timeout(Duration),
    #[error("pool closed")]
    Closed,
}

/// WorkerPool trait —— 抽象池池行为
#[async_trait]
pub trait WorkerPool: Send + Sync {
    /// 启动池池（拉取 broker → 派发 worker）
    async fn start(
        self: Arc<Self>,
        broker: Arc<dyn Broker>,
        cancel: CancellationToken,
    ) -> Result<(), PoolError>;

    /// 调整并发数（向上扩容立即生效，向下要等 worker 自然退出）
    async fn resize(&self, new_concurrency: u32) -> Result<(), PoolError>;

    /// 优雅停机：先停止拉取新 Task，再等待 in-flight 完成或 grace 超时
    async fn shutdown(&self) -> Result<(), PoolError>;

    /// 当前运行时统计
    async fn stats(&self) -> PoolStats;
}

/// 任务执行回调 —— 由 server crate 实现（具体调用 plugin gRPC）
#[async_trait]
pub trait TaskExecutor: Send + Sync {
    /// 执行单个 Task；server crate 在此调用 plugin.proto 的 Invoke / Assert
    async fn execute(&self, task: &Task) -> Result<TaskOutcome, PoolError>;
}

/// 任务结果
#[derive(Debug, Clone)]
pub struct TaskOutcome {
    pub status: aitest_core::TaskState,
    pub stdout: Option<String>,
    pub stderr: Option<String>,
    pub artifacts: Vec<ArtifactRef>,
}

#[derive(Debug, Clone)]
pub struct ArtifactRef {
    pub kind: String,
    pub uri: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_pool_config_is_sane() {
        let c = PoolConfig::default();
        assert!(c.concurrency > 0);
        assert!(c.shutdown_grace > Duration::ZERO);
        assert!(!c.topic.is_empty());
    }

    #[test]
    fn pool_stats_default_is_zero() {
        let s = PoolStats::default();
        assert_eq!(s.running, 0);
        assert_eq!(s.succeeded_total, 0);
    }
}
