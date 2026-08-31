//! aitest-plugin-sdk —— Rust 插件 SDK 骨架
//!
//! 关联设计：[`docs/architecture-v3-modules.md §7`](sdk)

use std::collections::HashMap;
use std::sync::Arc;

use async_trait::async_trait;
use serde_json::Value;

/// Manifest 声明
#[derive(Debug, Clone)]
pub struct Manifest {
    pub name: String,
    pub version: String,
    pub commands: Vec<CommandSpec>,
    pub assertors: Vec<AssertorSpec>,
}

/// CommandSpec 命令声明
#[derive(Debug, Clone)]
pub struct CommandSpec {
    pub name: String,
    pub description: String,
    pub side_effect: SideEffect,
    pub default_timeout_ms: u64,
}

/// AssertorSpec 断言器声明
#[derive(Debug, Clone)]
pub struct AssertorSpec {
    pub name: String,
    pub description: String,
}

/// SideEffect 副作用等级（与 plugin.proto SideEffectClass 对齐）
#[derive(Debug, Clone, Copy)]
pub enum SideEffect {
    Pure,
    Read,
    Local,
    Network,
    Destructive,
}

/// InvokeContext 调用上下文
pub struct InvokeContext {
    pub invocation_id: String,
    pub caller: String,
    pub trace_context: HashMap<String, String>,
}

/// AssertContext 断言上下文
pub struct AssertContext {
    pub invocation_id: String,
}

/// AssertResult 断言结果
#[derive(Debug, Clone)]
pub struct AssertResult {
    pub passed: bool,
    pub message: String,
}

impl AssertResult {
    pub fn pass() -> Self {
        Self { passed: true, message: String::new() }
    }
    pub fn fail(msg: impl Into<String>) -> Self {
        Self { passed: false, message: msg.into() }
    }
}

/// Plugin trait —— 插件作者实现
#[async_trait]
pub trait Plugin: Send + Sync {
    fn manifest(&self) -> Manifest;
    async fn invoke(&self, cmd: &str, args: Value, ctx: &InvokeContext) -> Result<Value, String>;
    async fn assert_or(&self, name: &str, value: Value, spec: Value, ctx: &AssertContext) -> Result<AssertResult, String>;
}

/// Serve 启动 gRPC server（骨架：仅打印 manifest）。
pub async fn serve<P: Plugin + 'static>(plugin: Arc<P>) -> Result<(), String> {
    let m = plugin.manifest();
    println!("[skeleton] plugin ready: {}@{}", m.name, m.version);
    println!("  commands: {}", m.commands.len());
    println!("  assertors: {}", m.assertors.len());
    // TODO S1: 真实 tonic server
    Ok(())
}
