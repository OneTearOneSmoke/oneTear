//! EXF gRPC handler trait —— 服务端抽象层
//!
//! 设计意图：
//! - 定义 EXF 对外暴露的 5 个 RPC method 签名（PlanService）
//! - 由 `main.rs` 配合 tonic codegen 实现
//! - Sprint 1 不接真实 codegen；先定义 trait + 数据结构
//!
//! 与 contracts/proto 的关系：
//! - plan.proto 中 PlanService 已有 5 个 RPC（Submit/Get/Cancel/List/Stream）
//! - 本 trait 抽象出一层，让实现可以独立于 tonic codegen 测试

use std::sync::Arc;

use aitest_scheduler::Scheduler;
use async_trait::async_trait;
use thiserror::Error;
use tokio_util::sync::CancellationToken;

/// PlanService 错误
#[derive(Debug, Error)]
pub enum PlanServiceError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("invalid argument: {0}")]
    InvalidArgument(String),
    #[error("scheduler: {0}")]
    Scheduler(String),
    #[error("internal: {0}")]
    Internal(String),
}

/// Submit 请求的内部表示（独立于 tonic codegen）
#[derive(Debug, Clone)]
pub struct SubmitPlanInput {
    pub plan_id: String,
    pub idempotency_key: Option<String>,
    pub validate_only: bool,
    pub specs: Vec<ResolvedCaseRef>,
}

/// 已解析的用例引用（来自 TCM；EXF 不直接读 TCM）
#[derive(Debug, Clone)]
pub struct ResolvedCaseRef {
    pub case_id: String,
    pub content_hash: String,
    pub semver: String,
    pub params: serde_json::Value,
    pub depends_on: Vec<String>,
    pub priority: i32,
    pub max_attempts: u32,
}

/// Submit 响应
#[derive(Debug, Clone)]
pub struct SubmitPlanOutput {
    pub plan_id: String,
    pub accepted: bool,
    pub estimated_start_ms: i64,
    pub resolved_case_count: u32,
}

/// Cancel 响应
#[derive(Debug, Clone)]
pub struct CancelPlanOutput {
    pub cancelled: bool,
    pub cancelled_tasks: u32,
    pub tasks_remaining: u32,
}

/// PlanService trait —— 5 个 RPC method
///
/// 实现由 tonic codegen + 本 trait 的具体适配器完成（Sprint 1+）。
#[async_trait]
pub trait PlanService: Send + Sync {
    async fn submit(
        &self,
        input: SubmitPlanInput,
        cancel: CancellationToken,
    ) -> Result<SubmitPlanOutput, PlanServiceError>;

    async fn get(&self, plan_id: &str) -> Result<PlanServiceStatus, PlanServiceError>;

    async fn cancel(
        &self,
        plan_id: &str,
        reason: &str,
        force: bool,
    ) -> Result<CancelPlanOutput, PlanServiceError>;

    async fn list(&self, page_size: u32, page_token: String)
        -> Result<PlanServicePage, PlanServiceError>;

    /// 流式订阅 Plan 状态变更（占位；Sprint 1 后端实现用 broker 事件流）
    async fn stream_events(
        &self,
        plan_id: &str,
    ) -> Result<tokio::sync::mpsc::Receiver<PlanEvent>, PlanServiceError>;
}

/// Plan 状态（gRPC 视图）
#[derive(Debug, Clone)]
pub struct PlanServiceStatus {
    pub plan_id: String,
    pub queued: u32,
    pub running: u32,
    pub succeeded: u32,
    pub failed: u32,
    pub canceled: u32,
}

/// 分页
#[derive(Debug, Clone)]
pub struct PlanServicePage {
    pub plans: Vec<PlanServiceStatus>,
    pub next_page_token: String,
}

/// 事件流（占位）
#[derive(Debug, Clone)]
pub enum PlanEvent {
    Queued,
    Started,
    Progress { completed: u32, total: u32 },
    Completed,
    Failed(String),
    Canceled,
    Log { level: String, message: String },
}

/// Scheduler-backed 实现（最小可用版；Sprint 1 替换为真实 broker-backed）
pub struct SchedulerBackedPlanService {
    scheduler: Arc<dyn Scheduler>,
}

impl SchedulerBackedPlanService {
    pub fn new(scheduler: Arc<dyn Scheduler>) -> Self {
        Self { scheduler }
    }
}

#[async_trait]
impl PlanService for SchedulerBackedPlanService {
    async fn submit(
        &self,
        input: SubmitPlanInput,
        cancel: CancellationToken,
    ) -> Result<SubmitPlanOutput, PlanServiceError> {
        let specs = input
            .specs
            .iter()
            .map(|r| aitest_scheduler::TaskSpec {
                case_id: r.case_id.clone(),
                content_hash: r.content_hash.clone(),
                semver: r.semver.clone(),
                params: r.params.clone(),
                depends_on: r.depends_on.clone(),
                priority: r.priority,
                max_attempts: r.max_attempts,
            })
            .collect::<Vec<_>>();

        let h = self
            .scheduler
            .submit(&input.plan_id, &specs, cancel)
            .await
            .map_err(|e| PlanServiceError::Scheduler(e.to_string()))?;

        Ok(SubmitPlanOutput {
            plan_id: h.plan_id,
            accepted: true,
            estimated_start_ms: 0,
            resolved_case_count: h.task_count,
        })
    }

    async fn get(&self,
        plan_id: &str,
    ) -> Result<PlanServiceStatus, PlanServiceError> {
        let s = self
            .scheduler
            .status(plan_id)
            .await
            .map_err(|e| match e {
                aitest_scheduler::SchedulerError::NotFound(_) => PlanServiceError::NotFound(plan_id.into()),
                other => PlanServiceError::Scheduler(other.to_string()),
            })?;
        Ok(PlanServiceStatus {
            plan_id: s.plan_id,
            queued: s.queued,
            running: s.running,
            succeeded: s.succeeded,
            failed: s.failed,
            canceled: s.canceled,
        })
    }

    async fn cancel(
        &self,
        plan_id: &str,
        reason: &str,
        force: bool,
    ) -> Result<CancelPlanOutput, PlanServiceError> {
        let s = self
            .scheduler
            .cancel(plan_id, reason, force)
            .await
            .map_err(|e| match e {
                aitest_scheduler::SchedulerError::NotFound(_) => PlanServiceError::NotFound(plan_id.into()),
                other => PlanServiceError::Scheduler(other.to_string()),
            })?;
        Ok(CancelPlanOutput {
            cancelled: s.cancelled_tasks > 0,
            cancelled_tasks: s.cancelled_tasks,
            tasks_remaining: s.tasks_remaining,
        })
    }

    async fn list(
        &self,
        _page_size: u32,
        _page_token: String,
    ) -> Result<PlanServicePage, PlanServiceError> {
        // Sprint 1 桩：Sprint 2 接入 PG backed 列表
        Ok(PlanServicePage {
            plans: vec![],
            next_page_token: String::new(),
        })
    }

    async fn stream_events(
        &self,
        _plan_id: &str,
    ) -> Result<tokio::sync::mpsc::Receiver<PlanEvent>, PlanServiceError> {
        // Sprint 1 桩：Sprint 3 接入 broker pub/sub
        let (_tx, rx) = tokio::sync::mpsc::channel(16);
        Ok(rx)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aitest_scheduler::{InMemoryScheduler, TaskSpec};

    #[tokio::test]
    async fn submit_then_get_via_service() {
        let sched: Arc<dyn Scheduler> = Arc::new(InMemoryScheduler::new());
        let svc = SchedulerBackedPlanService::new(sched);

        let out = svc
            .submit(
                SubmitPlanInput {
                    plan_id: "p1".into(),
                    idempotency_key: None,
                    validate_only: false,
                    specs: vec![ResolvedCaseRef {
                        case_id: "a".into(),
                        content_hash: "h".into(),
                        semver: "1.0.0".into(),
                        params: serde_json::json!({}),
                        depends_on: vec![],
                        priority: 0,
                        max_attempts: 3,
                    }],
                },
                CancellationToken::new(),
            )
            .await
            .unwrap();
        assert!(out.accepted);
        assert_eq!(out.resolved_case_count, 1);

        let st = svc.get("p1").await.unwrap();
        assert_eq!(st.queued, 1);
    }

    #[tokio::test]
    async fn cancel_via_service() {
        let sched: Arc<dyn Scheduler> = Arc::new(InMemoryScheduler::new());
        let svc = SchedulerBackedPlanService::new(sched);
        svc.submit(
            SubmitPlanInput {
                plan_id: "p".into(),
                idempotency_key: None,
                validate_only: false,
                specs: vec![ResolvedCaseRef {
                    case_id: "x".into(),
                    content_hash: "h".into(),
                    semver: "1".into(),
                    params: serde_json::json!({}),
                    depends_on: vec![],
                    priority: 0,
                    max_attempts: 3,
                }],
            },
            CancellationToken::new(),
        )
        .await
        .unwrap();
        let r = svc.cancel("p", "user", false).await.unwrap();
        assert_eq!(r.cancelled_tasks, 1);
    }
}
