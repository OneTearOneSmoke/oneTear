//! DagExpander —— 把已解析的 TaskSpec 列表展开为 DAG
//!
//! 职责：
//! - 输入：[`TaskSpec`] 列表（已由 TCM 解析完）
//! - 输出：[`aitest_core::Dag`]
//! - 内部职责：
//!   1. 校验 TaskSpec 间的 depends_on 合法性
//!   2. 检测循环依赖
//!   3. 注入默认依赖（无显式依赖时 = 顶层节点）
//!
//! 与 core::dag 的关系：
//! - `core::Dag` 是纯类型
//! - 本模块负责把外部输入转成 `core::Dag`

use aitest_core::{Dag, DagError, DagNode};
use async_trait::async_trait;
use thiserror::Error;

/// 已解析的 Task 规格（输入；与 contracts.proto ResolvedCaseRef 对应）
///
/// 注：scheduler crate 的旧 lib.rs 已定义同名 TaskSpec；这里只 re-export 以保持兼容。
pub use crate::TaskSpec;

/// DAG 展开器 trait
#[async_trait]
pub trait DagExpander: Send + Sync {
    /// 展开。
    ///
    /// `specs` 中每个 spec 的 `depends_on` 字段是 case_id 列表（可选）；
    /// 同一 plan 内 case_id 必须唯一。
    async fn expand(&self, specs: &[TaskSpec]) -> Result<Dag, ExpandError>;
}

/// 默认实现：直接转换 + 委托给 core::Dag 校验
pub struct DefaultExpander;

#[async_trait]
impl DagExpander for DefaultExpander {
    async fn expand(&self, specs: &[TaskSpec]) -> Result<Dag, ExpandError> {
        let nodes: Vec<DagNode> = specs
            .iter()
            .map(|s| DagNode {
                case_id: s.case_id.clone(),
                content_hash: s.content_hash.clone(),
                semver: s.semver.clone(),
                params: s.params.clone(),
                priority: s.priority,
                depends_on: s.depends_on.clone(),
            })
            .collect();

        Dag::from_nodes(nodes).map_err(ExpandError::from)
    }
}

/// 展开错误
#[derive(Debug, Error)]
pub enum ExpandError {
    #[error(transparent)]
    Dag(#[from] DagError),
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn s(id: &str, deps: &[&str]) -> TaskSpec {
        TaskSpec {
            case_id: id.into(),
            content_hash: format!("h-{}", id),
            semver: "1.0.0".into(),
            params: json!({}),
            priority: 0,
            depends_on: deps.iter().map(|x| x.to_string()).collect(),
        }
    }

    #[tokio::test]
    async fn expand_simple_chain() {
        let e = DefaultExpander;
        let dag = e
            .expand(&[s("a", &[]), s("b", &["a"]), s("c", &["b"])])
            .await
            .unwrap();
        assert_eq!(dag.len(), 3);
        let order: Vec<&str> = dag.topo().unwrap().into_iter().map(|n| n.case_id.as_str()).collect();
        assert_eq!(order, vec!["a", "b", "c"]);
    }

    #[tokio::test]
    async fn expand_rejects_cycle() {
        let e = DefaultExpander;
        let err = e.expand(&[s("a", &["b"]), s("b", &["a"])]).await.unwrap_err();
        assert!(matches!(err, ExpandError::Dag(DagError::Cycle)));
    }
}
