# CoPaw 局域网分布式智能体系统

## 📖 概述

这是一个完整的局域网分布式智能体协作系统，支持多台设备在同一局域网内自动发现、建立连接、协同工作。

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        局域网 (192.168.1.x)                          │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  CoPaw Node1 │◄──►│  CoPaw Node2 │◄──►│  CoPaw Node3 │           │
│  │  (Mac 主机)  │    │  (PC 主机)   │    │  (服务器)    │           │
│  │  192.168.1.10│    │  192.168.1.20│    │  192.168.1.30│           │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘           │
│         │                   │                   │                    │
│         └───────────────────┼───────────────────┘                    │
│                             ▼                                        │
│                  ┌──────────────────┐                                │
│                  │   去中心化 Mesh   │                                │
│                  └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔧 技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| **服务发现** | UDP 广播 | 端口 9527，自动发现局域网节点 |
| **长连接** | WebSocket | 端口 9528，持久化双向通信 |
| **心跳** | 自定义协议 | 5 秒间隔，15 秒超时检测 |
| **任务调度** | 异步队列 | 支持广播/指定节点执行 |
| **前端** | React + Ant Design | 实时监控与管理界面 |

## 📦 核心文件

```
src/copaw/app/lan_network/
├── __init__.py          # 核心网络通信模块
└── routes.py            # FastAPI 路由

console/src/pages/Control/LANNetwork/
├── index.tsx            # 前端管理页面
└── index.module.less    # 样式文件

console/src/api/modules/
└── lan.ts               # 前端 API 调用模块
```

## 🚀 快速开始

### 1. 在每台设备上安装 CoPaw

```bash
# 克隆最新代码
git clone https://github.com/huangrichao2020/CoPaw.git
cd CoPaw
pip install -e .

# 或者使用 pip 安装
pip install --upgrade copaw
```

### 2. 启动局域网网络

访问控制台：`http://localhost:8088/lan-network`

1. 点击 **"初始化网络"**
2. 配置节点名称（如：`CoPaw-Mac-Office`）
3. 设置 WebSocket 端口（默认 9528）
4. 点击 **"启动网络"**

### 3. 自动发现

系统会自动发现同一局域网内的其他 CoPaw 节点，并在列表中显示。

## 🔌 API 接口

### 初始化网络
```bash
POST /api/lan/init
{
  "node_name": "CoPaw-Node-1",
  "ws_port": 9528,
  "enable_discovery": true
}
```

### 启动网络
```bash
POST /api/lan/start
```

### 获取状态
```bash
GET /api/lan/status
```

### 获取节点列表
```bash
GET /api/lan/nodes
```

### 广播消息
```bash
POST /api/lan/broadcast
{
  "type": "broadcast",
  "payload": {"message": "Hello all nodes!"}
}
```

### 提交任务
```bash
POST /api/lan/task/submit?target_node=node_id
{
  "task_id": "task-001",
  "task_type": "stock_analysis",
  "payload": {"symbol": "AAPL"}
}
```

## 💡 使用场景

### 1. 分布式股票分析
```python
# 在主节点提交分析任务
task = Task(
    task_id="stock-001",
    task_type="stock_analysis",
    payload={"symbols": ["AAPL", "GOOGL", "MSFT"]}
)
await network.submit_task(task)  # 广播到所有节点
```

### 2. 跨设备数据同步
```python
# 同步会话数据
await network.broadcast_message(
    MessageType.SESSION_SYNC,
    {"session_id": "chat-123", "messages": [...]}
)
```

### 3. 负载均衡
```python
# 将任务分发到空闲节点
for symbol in stock_list:
    task = Task(task_type="fetch_price", payload={"symbol": symbol})
    await network.submit_task(task)  # 自动分配到空闲节点
```

## 🔍 通信协议

### 消息格式
```json
{
  "type": "task_request",
  "source_node": "node-abc123",
  "target_node": "node-xyz789",
  "timestamp": 1710000000.0,
  "payload": {...}
}
```

### 消息类型
- `heartbeat` - 心跳保活
- `discovery` - 发现广播
- `discovery_resp` - 发现响应
- `task_request` - 任务请求
- `task_response` - 任务响应
- `session_sync` - 会话同步
- `status_update` - 状态更新
- `broadcast` - 广播消息

## 🛡️ 注意事项

1. **防火墙配置**：确保 UDP 9527 和 TCP 9528 端口开放
2. **同一局域网**：所有设备必须在同一子网内
3. **端口冲突**：如 9528 被占用，可自定义其他端口
4. **节点命名**：建议使用有意义的名称便于识别

## 📊 状态监控

访问 `http://localhost:8088/lan-network` 查看：

- ✅ 当前节点状态（IDLE/BUSY/OFFLINE）
- ✅ 已知节点数量
- ✅ 活跃连接数
- ✅ 待处理任务数
- ✅ 节点详细信息列表

## 🔮 扩展开发

### 注册自定义任务处理器
```python
from copaw.app.lan_network import get_lan_network, Task

network = get_lan_network()

async def stock_handler(task: Task):
    symbol = task.payload.get("symbol")
    # 执行股票分析逻辑
    return {"price": 150.25, "change": "+2.3%"}

network.register_task_handler("stock_analysis", stock_handler)
```

### 前端调用示例
```typescript
// 初始化网络
await api.initNetwork({
  node_name: 'CoPaw-Mac',
  ws_port: 9528,
  enable_discovery: true,
});

// 获取节点列表
const nodes = await api.getNetworkNodes();

// 提交任务
await api.submitTask({
  task_id: 'task-001',
  task_type: 'stock_analysis',
  payload: { symbol: 'AAPL' },
});
```

## 📝 更新日志

### v0.1.0 (2026-03-09)
- ✅ UDP 广播服务发现
- ✅ WebSocket 长连接通信
- ✅ 心跳保活机制
- ✅ 任务调度框架
- ✅ 前端管理界面
- ✅ 多语言支持（zh/en/ru）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**作者**: CoPaw Team  
**日期**: 2026-03-09  
**版本**: v0.1.0
