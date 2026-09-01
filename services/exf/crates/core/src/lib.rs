//! aitest-core —— EXF 的核心类型与状态机
//!
//! 设计原则：
//! - 纯类型 + 状态转移表，**无 IO**
//! - 所有状态转移必须经过 [`StateMachine::can_transition`] 校验
//! - 与 contracts/proto 的关系：本 crate 定义 Rust 内部强类型；
//!   API 层负责与 protobuf message 转换
//!
//! 模块清单：
//! - 本文件：TaskState / StateMachine / Task
//! - `instance_id`：稳定任务实例 ID
//! - `dag`：DAG 节点与依赖图

pub mod dag;
pub mod instance_id;

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// 任务状态机
///
/// 状态图（详见 docs/architecture-v3-modules.md §4）：
///
/// ```text
/// Queued ─▶ Assigned ─▶ Running ─▶ Succeeded
///              │           │
///              │           ├─▶ Failed ─▶ Retrying ─▶ Running
///              │           ├─▶ Timeout
///              │           ├─▶ Canceled
///              │           ├─▶ Blocked
///              │           └─▶ Error
///              └─▶ Canceled
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskState {
    Queued,
    Assigned,
    Running,
    Succeeded,
    Failed,
    Retrying,
    Timeout,
    Canceled,
    Blocked,
    Error,
}

impl TaskState {
    /// 终态：Succeeded / Failed / Canceled / Timeout / Error
    pub fn is_terminal(self) -> bool {
        matches!(
            self,
            Self::Succeeded | Self::Failed | Self::Canceled | Self::Timeout | Self::Error
        )
    }

    /// 是否可被重试（Failed / Timeout / Error 可重试；Succeeded / Canceled 不可）
    pub fn is_retryable(self) -> bool {
        matches!(self, Self::Failed | Self::Timeout | Self::Error)
    }

    /// 状态名（与 contracts.proto Status 双向映射）
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Queued => "queued",
            Self::Assigned => "assigned",
            Self::Running => "running",
            Self::Succeeded => "succeeded",
            Self::Failed => "failed",
            Self::Retrying => "retrying",
            Self::Timeout => "timeout",
            Self::Canceled => "canceled",
            Self::Blocked => "blocked",
            Self::Error => "error",
        }
    }

    /// 从字符串还原（仅供反序列化用，未知值返回 Queued）
    pub fn from_str_loose(s: &str) -> Self {
        match s {
            "queued" => Self::Queued,
            "assigned" => Self::Assigned,
            "running" => Self::Running,
            "succeeded" => Self::Succeeded,
            "failed" => Self::Failed,
            "retrying" => Self::Retrying,
            "timeout" => Self::Timeout,
            "canceled" => Self::Canceled,
            "blocked" => Self::Blocked,
            "error" => Self::Error,
            _ => Self::Queued,
        }
    }
}

/// 非法状态转移错误
#[derive(Debug, Error, Clone, PartialEq, Eq)]
#[error("illegal state transition: {from:?} -> {to:?}")]
pub struct IllegalTransition {
    pub from: TaskState,
    pub to: TaskState,
}

/// 状态机 trait
///
/// 所有 Task 实例化时必须实现本 trait；EXF 在每个状态变更时调用
/// `can_transition` 校验，不合法直接拒绝。
pub trait StateMachine {
    fn state(&self) -> TaskState;

    /// 校验 from → to 是否合法
    fn can_transition(from: TaskState, to: TaskState) -> bool {
        use TaskState::*;
        match (from, to) {
            // 入队 → 分配
            (Queued, Assigned) => true,
            // 分配 → 运行
            (Assigned, Running) => true,
            // 运行 → 各终态
            (Running, Succeeded) => true,
            (Running, Failed) => true,
            (Running, Timeout) => true,
            (Running, Canceled) => true,
            (Running, Blocked) => true,
            (Running, Error) => true,
            // 运行失败 → 重试
            (Running, Retrying) => true,
            (Failed, Retrying) => true,
            (Timeout, Retrying) => true,
            (Error, Retrying) => true,
            // 重试 → 入队
            (Retrying, Queued) => true,
            // 阻塞 → 运行
            (Blocked, Running) => true,
            // 任意非终态 → 取消
            (Queued | Assigned | Running | Retrying | Blocked, Canceled) => true,
            // 终态不可再转移
            _ if from.is_terminal() => false,
            _ => false,
        }
    }

    /// 执行状态转移；不合法返回 IllegalTransition
    fn transition(&mut self, to: TaskState) -> Result<(), IllegalTransition> {
        let from = self.state();
        if !Self::can_transition(from, to) {
            return Err(IllegalTransition { from, to });
        }
        self.set_state(to);
        Ok(())
    }

    /// 设置状态（子类实现；通常私有 fn 由 transition 内部调用）
    fn set_state(&mut self, new_state: TaskState);
}

/// Task 实例（与 contracts.proto Result 对应但更精简）
#[derive(Debug, Clone)]
pub struct Task {
    /// 实例 ID —— 见 [`instance_id::InstanceId`]
    pub instance_id: String,
    pub plan_id: String,
    pub case_id: String,
    pub content_hash: String,
    pub semver: String,
    pub params: serde_json::Value,
    pub state: TaskState,
    pub attempts: u32,
    /// 可重试次数上限（来自 plan 或 case）
    pub max_attempts: u32,
}

impl StateMachine for Task {
    fn state(&self) -> TaskState {
        self.state
    }

    fn set_state(&mut self, new_state: TaskState) {
        self.state = new_state;
    }
}

impl Task {
    pub fn new(
        plan_id: impl Into<String>,
        case_id: impl Into<String>,
        content_hash: impl Into<String>,
        semver: impl Into<String>,
        params: serde_json::Value,
    ) -> Self {
        let plan_id = plan_id.into();
        let case_id = case_id.into();
        let content_hash = content_hash.into();
        let semver = semver.into();
        let instance_id = crate::instance_id::InstanceId::new(
            &plan_id,
            &case_id,
            &content_hash,
            &semver,
            &params,
        )
        .into_string();
        Self {
            instance_id,
            plan_id,
            case_id,
            content_hash,
            semver,
            params,
            state: TaskState::Queued,
            attempts: 0,
            max_attempts: 3,
        }
    }

    /// 是否还能继续尝试
    pub fn can_retry(&self) -> bool {
        self.attempts < self.max_attempts
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn queued_to_assigned_is_legal() {
        assert!(Task::can_transition(TaskState::Queued, TaskState::Assigned));
    }

    #[test]
    fn queued_to_running_is_illegal() {
        assert!(!Task::can_transition(TaskState::Queued, TaskState::Running));
    }

    #[test]
    fn succeeded_is_terminal() {
        assert!(TaskState::Succeeded.is_terminal());
        assert!(!Task::can_transition(TaskState::Succeeded, TaskState::Running));
    }

    #[test]
    fn retry_transitions_legal() {
        assert!(Task::can_transition(TaskState::Failed, TaskState::Retrying));
        assert!(Task::can_transition(TaskState::Retrying, TaskState::Queued));
    }

    #[test]
    fn instance_id_is_stable() {
        let t1 = Task::new("p1", "ai.sort", "abcdef0123456789", "1.0.0", serde_json::json!({"a":1}));
        let t2 = Task::new("p1", "ai.sort", "abcdef0123456789", "1.0.0", serde_json::json!({"a":1}));
        assert_eq!(t1.instance_id, t2.instance_id);
    }

    #[test]
    fn from_str_roundtrip() {
        for s in [
            TaskState::Queued,
            TaskState::Running,
            TaskState::Succeeded,
            TaskState::Failed,
        ] {
            assert_eq!(TaskState::from_str_loose(s.as_str()), s);
        }
    }

    #[test]
    fn retryable_states() {
        assert!(TaskState::Failed.is_retryable());
        assert!(TaskState::Timeout.is_retryable());
        assert!(!TaskState::Succeeded.is_retryable());
        assert!(!TaskState::Canceled.is_retryable());
    }
}
