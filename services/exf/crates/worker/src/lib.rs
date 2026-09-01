//! aitest-worker —— Worker + WorkerPool
//!
//! 关联设计：[`docs/architecture-v3-modules.md §4`](worker)
//!
//! 模块清单：
//! - 本文件：Worker trait + WorkerHandle
//! - `pool`：WorkerPool trait + PoolConfig + PoolStats + TaskExecutor

pub mod pool;

pub use pool::{PoolConfig, PoolStats, TaskExecutor, TaskOutcome, WorkerPool};

use std::sync::Arc;
use std::time::Duration;

use aitest_broker::{Broker, BrokerError};
use async_trait::async_trait;
use thiserror::Error;
use tokio_util::sync::CancellationToken;

/// Worker 句柄
pub struct WorkerHandle {
    pub worker_id: String,
}

/// Worker 错误
#[derive(Debug, Error)]
pub enum WorkerError {
    #[error("broker: {0}")]
    Broker(#[from] BrokerError),
    #[error("plugin call: {0}")]
    Plugin(String),
    #[error("timeout after {0:?}")]
    Timeout(Duration),
}

/// Worker trait —— 由 server crate 组合 broker + plugin client 实现。
#[async_trait]
pub trait Worker: Send + Sync {
    /// 启动 Worker 协程，持续从 broker 拉取 Task 并执行
    async fn run(self: Arc<Self>, broker: Arc<dyn Broker>, cancel: CancellationToken) -> WorkerHandle;

    /// 优雅停机：完成 in-flight Task 后退出
    async fn shutdown(&self, grace: Duration) -> Result<(), WorkerError>;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn worker_handle_constructs() {
        let h = WorkerHandle {
            worker_id: "w-1".into(),
        };
        assert_eq!(h.worker_id, "w-1");
    }
}
