//! aitest-broker —— Broker trait + InMemory 骨架
//!
//! 关联设计：[`docs/architecture-v3-modules.md §4`](broker)
//!
//! Sprint 1 用 InMemory 实现；Sprint 3 切换为 NATS JetStream。

use std::sync::Arc;

use async_trait::async_trait;
use bytes::Bytes;
use thiserror::Error;
use tokio::sync::Mutex;

/// 消息 ID（ACK / NACK 用）
pub type MessageId = u64;

/// 订阅句柄
pub struct Subscription {
    pub messages: tokio::sync::mpsc::Receiver<(MessageId, Bytes)>,
}

/// Broker 错误
#[derive(Debug, Error)]
pub enum BrokerError {
    #[error("broker closed")]
    Closed,
    #[error("topic not found: {0}")]
    TopicNotFound(String),
    #[error("io error: {0}")]
    Io(String),
}

/// Broker trait —— Worker 与 Scheduler 之间的解耦点。
#[async_trait]
pub trait Broker: Send + Sync {
    async fn publish(&self, topic: &str, msg: Bytes) -> Result<(), BrokerError>;
    async fn subscribe(&self, topic: &str) -> Result<Subscription, BrokerError>;
    async fn ack(&self, msg: MessageId) -> Result<(), BrokerError>;
    async fn nack(&self, msg: MessageId, reason: &str) -> Result<(), BrokerError>;
}

/// InMemory Broker 骨架（仅供单进程测试）。
pub struct InMemoryBroker {
    topics: Arc<Mutex<std::collections::HashMap<String, Vec<Bytes>>>>,
    next_id: Arc<Mutex<u64>>,
}

impl InMemoryBroker {
    pub fn new() -> Self {
        Self {
            topics: Arc::new(Mutex::new(std::collections::HashMap::new())),
            next_id: Arc::new(Mutex::new(0)),
        }
    }
}

impl Default for InMemoryBroker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Broker for InMemoryBroker {
    async fn publish(&self, topic: &str, msg: Bytes) -> Result<(), BrokerError> {
        let mut t = self.topics.lock().await;
        t.entry(topic.to_string()).or_default().push(msg);
        let mut id = self.next_id.lock().await;
        *id += 1;
        Ok(())
    }

    async fn subscribe(&self, topic: &str) -> Result<Subscription, BrokerError> {
        let (tx, rx) = tokio::sync::mpsc::channel(64);
        let topics = self.topics.clone();
        let topic = topic.to_string();
        tokio::spawn(async move {
            let t = topics.lock().await;
            if let Some(msgs) = t.get(&topic) {
                let mut id = 0u64;
                for m in msgs.iter() {
                    if tx.send((id, m.clone())).await.is_err() {
                        return;
                    }
                    id += 1;
                }
            }
        });
        Ok(Subscription { messages: rx })
    }

    async fn ack(&self, _msg: MessageId) -> Result<(), BrokerError> {
        Ok(())
    }

    async fn nack(&self, _msg: MessageId, _reason: &str) -> Result<(), BrokerError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn publish_subscribe_roundtrip() {
        let b = InMemoryBroker::new();
        b.publish("t1", Bytes::from_static(b"hello")).await.unwrap();
        let mut sub = b.subscribe("t1").await.unwrap();
        let (id, msg) = sub.messages.recv().await.unwrap();
        assert_eq!(id, 0);
        assert_eq!(msg, Bytes::from_static(b"hello"));
    }
}
