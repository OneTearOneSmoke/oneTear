//! DAG —— Plan 展开后的依赖图
//!
//! 设计意图（与 `aitest-scheduler::dag` 的差异）：
//! - 本模块定义**纯类型**（DagNode / Dag / 边关系），不解析如何构造
//! - 构造逻辑（含拓扑排序 / 循环检测）在 scheduler crate
//! - 协议映射在 server crate
//!
//! 关键约束：
//! - 节点 ID 用 case_id（**短**），便于运维排查
//! - 边用 depends_on（Vec<case_id>），不强类型化依赖关系
//! - Dag 提供 iter / topo / ready 三类只读视图

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// DAG 节点 —— 一个待执行的用例
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DagNode {
    /// 用例 ID（人类可读，非内容寻址）
    pub case_id: String,

    /// 内容哈希（用于去重/缓存命中判断）
    pub content_hash: String,

    /// 语义版本
    pub semver: String,

    /// 参数（已渲染：模板填充后的最终 JSON）
    pub params: serde_json::Value,

    /// 优先级（数值越大越优先；0 = 默认）
    pub priority: i32,

    /// 依赖的 case_id 列表（必须全部 succeeded 才执行）
    #[serde(default)]
    pub depends_on: Vec<String>,
}

/// DAG —— 一份 Plan 展开后的全部节点
#[derive(Debug, Clone, Default)]
pub struct Dag {
    nodes: Vec<DagNode>,
    index: HashMap<String, usize>,
}

impl Dag {
    /// 构造空 DAG。
    pub fn new() -> Self {
        Self::default()
    }

    /// 构造（内部用）。`nodes` 内部 case_id 必须唯一。
    pub fn from_nodes(nodes: Vec<DagNode>) -> Result<Self, DagError> {
        let mut index = HashMap::with_capacity(nodes.len());
        for (i, n) in nodes.iter().enumerate() {
            if index.insert(n.case_id.clone(), i).is_some() {
                return Err(DagError::DuplicateCase(n.case_id.clone()));
            }
        }
        // 校验所有 depends_on 引用的 case_id 存在
        let keys: HashSet<&str> = index.keys().map(|s| s.as_str()).collect();
        for n in &nodes {
            for dep in &n.depends_on {
                if !keys.contains(dep.as_str()) {
                    return Err(DagError::UnknownDependency {
                        case_id: n.case_id.clone(),
                        dep: dep.clone(),
                    });
                }
            }
        }
        Ok(Self { nodes, index })
    }

    /// 节点数。
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    /// 是否空。
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// 按 case_id 查找节点。
    pub fn get(&self, case_id: &str) -> Option<&DagNode> {
        self.index.get(case_id).map(|&i| &self.nodes[i])
    }

    /// 全部节点（按插入顺序）。
    pub fn nodes(&self) -> &[DagNode] {
        &self.nodes
    }

    /// 就绪节点：所有依赖均已 succeeded。
    ///
    /// `succeeded` 是已完成的 case_id 集合。
    pub fn ready(&self, succeeded: &HashSet<String>) -> Vec<&DagNode> {
        self.nodes
            .iter()
            .filter(|n| {
                n.depends_on
                    .iter()
                    .all(|d| succeeded.contains(d.as_str()))
            })
            .collect()
    }

    /// 拓扑排序（Kahn）。返回拓扑序；含环时返回错误。
    pub fn topo(&self) -> Result<Vec<&DagNode>, DagError> {
        let mut in_deg: HashMap<&str, usize> = HashMap::new();
        let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
        for n in &self.nodes {
            in_deg.entry(n.case_id.as_str()).or_insert(0);
            adj.entry(n.case_id.as_str()).or_default();
            for dep in &n.depends_on {
                *in_deg.entry(n.case_id.as_str()).or_insert(0) += 1;
                adj.entry(dep.as_str()).or_default().push(&n.case_id);
            }
        }
        let mut ready: Vec<&str> = in_deg
            .iter()
            .filter(|(_, &v)| v == 0)
            .map(|(k, _)| *k)
            .collect();
        ready.sort();

        let mut order = Vec::with_capacity(self.nodes.len());
        while let Some(c) = ready.pop() {
            order.push(c);
            for nxt in adj.get(c).cloned().unwrap_or_default() {
                let d = in_deg.get_mut(nxt).unwrap();
                *d -= 1;
                if *d == 0 {
                    ready.push(nxt);
                }
            }
        }
        if order.len() != self.nodes.len() {
            return Err(DagError::Cycle);
        }
        Ok(order
            .into_iter()
            .map(|c| self.get(c).expect("in index"))
            .collect())
    }
}

/// DAG 构造/校验错误
#[derive(Debug, thiserror::Error)]
pub enum DagError {
    #[error("duplicate case_id: {0}")]
    DuplicateCase(String),

    #[error("unknown dependency: case '{case_id}' depends on '{dep}' which is not in DAG")]
    UnknownDependency { case_id: String, dep: String },

    #[error("cycle detected in DAG")]
    Cycle,
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn n(id: &str, deps: &[&str]) -> DagNode {
        DagNode {
            case_id: id.into(),
            content_hash: format!("h-{}", id),
            semver: "1.0.0".into(),
            params: json!({}),
            priority: 0,
            depends_on: deps.iter().map(|s| s.to_string()).collect(),
        }
    }

    #[test]
    fn empty_dag_is_ok() {
        let d = Dag::from_nodes(vec![]).unwrap();
        assert!(d.is_empty());
        assert!(d.topo().unwrap().is_empty());
    }

    #[test]
    fn duplicate_case_rejected() {
        let err = Dag::from_nodes(vec![n("a", &[]), n("a", &[])]).unwrap_err();
        assert!(matches!(err, DagError::DuplicateCase(_)));
    }

    #[test]
    fn unknown_dependency_rejected() {
        let err = Dag::from_nodes(vec![n("a", &["missing"])]).unwrap_err();
        assert!(matches!(err, DagError::UnknownDependency { .. }));
    }

    #[test]
    fn cycle_detected() {
        let err = Dag::from_nodes(vec![n("a", &["b"]), n("b", &["a"])]).unwrap_err();
        assert!(matches!(err, DagError::Cycle));
    }

    #[test]
    fn topo_orders_respect_dependencies() {
        let d = Dag::from_nodes(vec![n("c", &["a", "b"]), n("b", &["a"]), n("a", &[])]).unwrap();
        let order: Vec<&str> = d.topo().unwrap().into_iter().map(|n| n.case_id.as_str()).collect();
        let pos = |x: &str| order.iter().position(|y| *y == x).unwrap();
        assert!(pos("a") < pos("b"));
        assert!(pos("b") < pos("c"));
    }

    #[test]
    fn ready_filters_unsatisfied_deps() {
        let d = Dag::from_nodes(vec![n("a", &[]), n("b", &["a"])]).unwrap();
        let r0 = d.ready(&HashSet::new());
        assert_eq!(r0.len(), 1);
        assert_eq!(r0[0].case_id, "a");

        let mut done = HashSet::new();
        done.insert("a".to_string());
        let r1 = d.ready(&done);
        assert_eq!(r1.len(), 1);
        assert_eq!(r1[0].case_id, "b");
    }
}
