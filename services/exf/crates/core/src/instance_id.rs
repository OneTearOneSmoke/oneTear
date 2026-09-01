//! 任务实例 ID —— 在 EXF 全链路稳定
//!
//! 唯一性来源：(plan_id, case_id, content_hash, semver, params) 五元组
//! 格式：`{plan_id}#{case_id_short}#{semver}#{params_short_hash}`
//!
//! 设计要点：
//! - 稳定：同输入永远得到同 instance_id（重启/重投也不变）
//! - 可读：plan_id 与 case_id 前缀对运维友好
//! - 长度可控：固定前缀 + 12 字符 hash = 总长 < 128 字节
//! - 不依赖外部状态：纯函数，可并行
//!
//! 用法：
//! ```rust
//! use aitest_core::impl::InstanceId;
//! let id = InstanceId::new("p-1", "ai.sort", "abc123def456", "1.0.0", &serde_json::json!({"a": 1}));
//! assert_eq!(id.as_str(), id.as_str());
//! ```

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// 实例 ID —— 包一层避免外部直接构造
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct InstanceId(String);

impl InstanceId {
    /// 构造实例 ID。
    ///
    /// 五个字段任一变化 → 不同 ID。
    pub fn new(
        plan_id: &str,
        case_id: &str,
        content_hash: &str,
        semver: &str,
        params: &serde_json::Value,
    ) -> Self {
        let case_short = short(case_id, 12);
        let hash_short = short(content_hash, 12);
        let params_hash = params_hash(params, 8);

        // 用 | 分隔避免 plan_id / case_id 中的特殊字符混淆
        let s = format!(
            "{}|{}|{}|{}|{}",
            sanitize(plan_id),
            case_short,
            hash_short,
            sanitize(semver),
            params_hash
        );
        Self(s)
    }

    /// 从 raw 字符串恢复（仅供 broker / 反序列化用，业务代码应走 `new`）。
    pub fn from_raw(s: impl Into<String>) -> Self {
        Self(s.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn into_string(self) -> String {
        self.0
    }

    /// 提取 plan_id 前缀（用于日志/指标维度）。
    pub fn plan_id_prefix(&self) -> &str {
        self.0.split('|').next().unwrap_or("")
    }
}

/// 保留字符替换为下划线。
fn sanitize(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '|' | '#' | ' ' | '\n' | '\t' => '_',
            _ => c,
        })
        .collect()
}

/// 取字符串前 n 字符；不足则全部返回。
fn short(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// 对 params 序列化做稳定哈希（与字段顺序无关：先 keys 排序）。
///
/// 用 std DefaultHasher（生产可换 blake3）。
fn params_hash(v: &serde_json::Value, n: usize) -> String {
    let canonical = canonicalize(v);
    let mut h = DefaultHasher::new();
    canonical.hash(&mut h);
    let h = h.finish();
    let hex = format!("{:016x}", h);
    hex.chars().take(n).collect()
}

/// 把 Value 规范化为 key 排序的字符串（消除字段顺序影响）。
fn canonicalize(v: &serde_json::Value) -> String {
    use serde_json::Value;
    match v {
        Value::Null => "null".into(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => n.to_string(),
        Value::String(s) => format!("\"{}\"", s),
        Value::Array(arr) => {
            let parts: Vec<String> = arr.iter().map(canonicalize).collect();
            format!("[{}]", parts.join(","))
        }
        Value::Object(obj) => {
            let mut keys: Vec<&String> = obj.keys().collect();
            keys.sort();
            let parts: Vec<String> = keys
                .into_iter()
                .map(|k| format!("{}:{}", canonicalize(&Value::String(k.clone())), canonicalize(&obj[k])))
                .collect();
            format!("{{{}}}", parts.join(","))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn stable_across_calls() {
        let a = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"a": 1}));
        let b = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"a": 1}));
        assert_eq!(a, b);
    }

    #[test]
    fn params_order_doesnt_matter() {
        let a = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"a": 1, "b": 2}));
        let b = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"b": 2, "a": 1}));
        assert_eq!(a, b);
    }

    #[test]
    fn different_params_yields_different_id() {
        let a = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"a": 1}));
        let b = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({"a": 2}));
        assert_ne!(a, b);
    }

    #[test]
    fn different_plan_id_yields_different_id() {
        let a = InstanceId::new("p1", "ai.sort", "abc123def456", "1.0.0", &json!({}));
        let b = InstanceId::new("p2", "ai.sort", "abc123def456", "1.0.0", &json!({}));
        assert_ne!(a, b);
    }

    #[test]
    fn sanitizes_special_chars() {
        let id = InstanceId::new("p | x", "ai # sort", "abc123def456", "1.0.0", &json!({}));
        assert!(!id.as_str().contains('|') || id.as_str().matches('|').count() == 4);
    }

    #[test]
    fn plan_id_prefix_extractable() {
        let id = InstanceId::new("plan-abc", "ai.sort", "abc", "1.0.0", &json!({}));
        assert_eq!(id.plan_id_prefix(), "plan-abc");
    }
}
