//! aitest-worker —— Worker Pool
//!
//! 关联设计：[`docs/architecture-v3-modules.md §4`](worker)

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

/// 简易 Worker Pool 骨架：仅记录 worker 数量，未真实拉取 broker。
pub struct WorkerPool {
    concurrency: u32,
}

impl WorkerPool {
    pub fn new(concurrency: u32) -> Self {
        Self { concurrency }
    }

    pub fn concurrency(&self) -> u32 {
        self.concurrency
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pool_records_concurrency() {
        let p = WorkerPool::new(100);
        assert_eq!(p.concurrency(), 100);
    }
}
