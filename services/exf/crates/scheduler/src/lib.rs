//! aitest-scheduler —— Plan → DAG → Task
//!
//! 关联设计：[`docs/architecture-v3-modules.md §4`](scheduler)
//!
//! 模块清单：
//! - 本文件：Scheduler trait + InMemoryScheduler + PlanHandle/PlanStatus/CancelSummary
//! - `dag`：DagExpander trait + DefaultExpander

pub mod dag;

use std::sync::Arc;

use aitest_core::{Task, TaskState};
use async_trait::async_trait;
use thiserror::Error;
use tokio_util::sync::CancellationToken;

/// Plan 句柄（提交后返回）
#[derive(Debug, Clone)]
pub struct PlanHandle {
    pub plan_id: String,
    pub task_count: u32,
}

/// Plan 状态
#[derive(Debug, Clone)]
pub struct PlanStatus {
    pub plan_id: String,
    pub queued: u32,
    pub running: u32,
    pub succeeded: u32,
    pub failed: u32,
    pub canceled: u32,
}

/// 取消计划汇总
#[derive(Debug, Clone)]
pub struct CancelSummary {
    pub plan_id: String,
    pub cancelled_tasks: u32,
    pub tasks_remaining: u32,
}

/// 调度器错误
#[derive(Debug, Error)]
pub enum SchedulerError {
    #[error("plan not found: {0}")]
    NotFound(String),
    #[error("broker error: {0}")]
    Broker(String),
    #[error("invalid plan: {0}")]
    Invalid(String),
    #[error("canceled")]
    Canceled,
}

/// 调度器 trait
///
/// 实现要点：
/// - `submit` 必须返回 `PlanHandle`（异步立即返回，不等执行完成）
/// - `cancel(force=true)` 时已 Running 的 Task 也立即停止（依赖 worker.shutdown）
#[async_trait]
pub trait Scheduler: Send + Sync {
    /// 提交一份 Plan，立即展开 DAG 并把 Task 推到 Broker
    async fn submit(
        &self,
        plan_id: &str,
        resolved: &[TaskSpec],
        cancel: CancellationToken,
    ) -> Result<PlanHandle, SchedulerError>;

    /// 取消整个 Plan
    async fn cancel(
        &self,
        plan_id: &str,
        reason: &str,
        force: bool,
    ) -> Result<CancelSummary, SchedulerError>;

    /// 查询 Plan 状态
    async fn status(&self, plan_id: &str) -> Result<PlanStatus, SchedulerError>;
}

/// TaskSpec —— 已解析的 Task 规格（由 Plan.Submit 时 TCM 提供）
///
/// 字段扩展（Sprint 1）：
/// - `depends_on`：DAG 依赖（Sprint 1 新增；之前未使用）
/// - `max_attempts`：每个 Task 的最大重试次数（默认 3）
#[derive(Debug, Clone)]
pub struct TaskSpec {
    pub case_id: String,
    pub content_hash: String,
    pub semver: String,
    pub params: serde_json::Value,
    pub priority: i32,
    #[serde(default)]
    pub depends_on: Vec<String>,
    #[serde(default = "default_max_attempts")]
    pub max_attempts: u32,
}

fn default_max_attempts() -> u32 {
    3
}

impl TaskSpec {
    pub fn into_task(&self, plan_id: &str) -> Task {
        let mut t = Task::new(
            plan_id,
            &self.case_id,
            &self.content_hash,
            &self.semver,
            self.params.clone(),
        );
        t.max_attempts = self.max_attempts;
        t
    }
}

/// InMemoryScheduler 骨架版：仅记录 plan → tasks 映射，未连 Broker。
///
/// 后续 Sprint 1 替换为真实 broker-backed 实现。
pub struct InMemoryScheduler {
    inner: Arc<tokio::sync::RwLock<SchedulerState>>,
}

#[derive(Default)]
struct SchedulerState {
    plans: std::collections::HashMap<String, Vec<Task>>,
}

impl InMemoryScheduler {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(tokio::sync::RwLock::new(SchedulerState::default())),
        }
    }
}

#[async_trait]
impl Scheduler for InMemoryScheduler {
    async fn submit(
        &self,
        plan_id: &str,
        resolved: &[TaskSpec],
        _cancel: CancellationToken,
    ) -> Result<PlanHandle, SchedulerError> {
        let tasks: Vec<Task> = resolved
            .iter()
            .map(|s| s.into_task(plan_id))
            .collect();
        let mut st = self.inner.write().await;
        st.plans.insert(plan_id.to_string(), tasks.clone());
        Ok(PlanHandle {
            plan_id: plan_id.to_string(),
            task_count: tasks.len() as u32,
        })
    }

    async fn cancel(
        &self,
        plan_id: &str,
        _reason: &str,
        _force: bool,
    ) -> Result<CancelSummary, SchedulerError> {
        let mut st = self.inner.write().await;
        let tasks = st
            .plans
            .get_mut(plan_id)
            .ok_or_else(|| SchedulerError::NotFound(plan_id.to_string()))?;
        let mut cancelled = 0;
        for t in tasks.iter_mut() {
            if !t.state.is_terminal() {
                let _ = t.transition(TaskState::Canceled);
                cancelled += 1;
            }
        }
        Ok(CancelSummary {
            plan_id: plan_id.to_string(),
            cancelled_tasks: cancelled,
            tasks_remaining: 0,
        })
    }

    async fn status(&self, plan_id: &str) -> Result<PlanStatus, SchedulerError> {
        let st = self.inner.read().await;
        let tasks = st
            .plans
            .get(plan_id)
            .ok_or_else(|| SchedulerError::NotFound(plan_id.to_string()))?;
        let mut s = PlanStatus {
            plan_id: plan_id.to_string(),
            queued: 0,
            running: 0,
            succeeded: 0,
            failed: 0,
            canceled: 0,
        };
        for t in tasks {
            match t.state {
                TaskState::Queued => s.queued += 1,
                TaskState::Running | TaskState::Assigned => s.running += 1,
                TaskState::Succeeded => s.succeeded += 1,
                TaskState::Failed | TaskState::Timeout | TaskState::Error => s.failed += 1,
                TaskState::Canceled => s.canceled += 1,
                _ => {}
            }
        }
        Ok(s)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aitest_core::StateMachine;

    #[tokio::test]
    async fn submit_then_status() {
        let sched = InMemoryScheduler::new();
        let specs = vec![
            TaskSpec {
                case_id: "ai.sort".into(),
                content_hash: "abc".into(),
                semver: "1.0.0".into(),
                params: serde_json::json!({}),
                priority: 0,
                depends_on: vec![],
                max_attempts: 3,
            },
            TaskSpec {
                case_id: "ai.eval".into(),
                content_hash: "def".into(),
                semver: "1.0.0".into(),
                params: serde_json::json!({}),
                priority: 0,
                depends_on: vec![],
                max_attempts: 3,
            },
        ];
        let h = sched
            .submit("plan-1", &specs, CancellationToken::new())
            .await
            .unwrap();
        assert_eq!(h.task_count, 2);
        let s = sched.status("plan-1").await.unwrap();
        assert_eq!(s.queued, 2);
    }

    #[tokio::test]
    async fn cancel_terminates_non_terminal() {
        let sched = InMemoryScheduler::new();
        let specs = vec![TaskSpec {
            case_id: "x".into(),
            content_hash: "h".into(),
            semver: "1".into(),
            params: serde_json::json!({}),
            priority: 0,
            depends_on: vec![],
            max_attempts: 3,
        }];
        sched
            .submit("plan-x", &specs, CancellationToken::new())
            .await
            .unwrap();
        let summary = sched.cancel("plan-x", "user", false).await.unwrap();
        assert_eq!(summary.cancelled_tasks, 1);
    }
}
