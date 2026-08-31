//! aitest-core —— EXF 的核心类型与状态机
//!
//! 设计原则：
//! - 纯类型 + 状态转移表，**无 IO**
//! - 所有状态转移必须经过 [`StateMachine::can_transition`] 校验
//! - 与 contracts/proto 的关系：本 crate 定义 Rust 内部强类型；
//!   API 层负责与 protobuf message 转换

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
    pub instance_id: String,
    pub plan_id: String,
    pub case_id: String,
    pub content_hash: String,
    pub semver: String,
    pub params: serde_json::Value,
    pub state: TaskState,
    pub attempts: u32,
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
        let instance_id = format!(
            "{}#{}#{}#{}",
            case_id,
            &content_hash[..12.min(content_hash.len())],
            semver,
            short_hash(&params),
        );
        Self {
            instance_id,
            plan_id,
            case_id,
            content_hash,
            semver,
            params,
            state: TaskState::Queued,
            attempts: 0,
        }
    }
}

fn short_hash(v: &serde_json::Value) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut h = DefaultHasher::new();
    v.to_string().hash(&mut h);
    format!("{:016x}", h.finish())[..8].to_string()
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
    fn instance_id_is_stable() {
        let t1 = Task::new("p1", "ai.sort", "abcdef0123456789", "1.0.0", serde_json::json!({"a":1}));
        let t2 = Task::new("p1", "ai.sort", "abcdef0123456789", "1.0.0", serde_json::json!({"a":1}));
        assert_eq!(t1.instance_id, t2.instance_id);
    }
}
