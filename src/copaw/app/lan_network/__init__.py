# -*- coding: utf-8 -*-
"""
CoPaw 局域网分布式智能体通信模块

支持：
1. 自动发现局域网内的 CoPaw 节点
2. WebSocket 长连接通信
3. 分布式任务调度与执行
4. 跨设备会话同步
"""

import asyncio
import json
import socket
import hashlib
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import websockets
from websockets.server import serve
from websockets.client import connect
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    HEARTBEAT = "heartbeat"           # 心跳
    DISCOVERY = "discovery"           # 发现广播
    DISCOVERY_RESP = "discovery_resp" # 发现响应
    TASK_REQUEST = "task_request"     # 任务请求
    TASK_RESPONSE = "task_response"   # 任务响应
    SESSION_SYNC = "session_sync"     # 会话同步
    STATUS_UPDATE = "status_update"   # 状态更新
    BROADCAST = "broadcast"           # 广播消息


class NodeStatus(Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    host: str
    port: int
    ws_port: int
    name: str
    status: str = NodeStatus.IDLE.value
    capabilities: List[str] = field(default_factory=list)
    last_heartbeat: float = 0
    version: str = "0.0.5"
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "NodeInfo":
        return cls(**data)


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    source_node: str
    target_node: Optional[str] = None
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    timeout: int = 300
    result: Optional[Any] = None
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None


class LANMeshNetwork:
    """
    局域网 Mesh 网络通信核心类
    
    功能：
    1. 节点发现与注册
    2. WebSocket 长连接管理
    3. 消息路由与转发
    4. 任务调度与执行
    """
    
    DISCOVERY_PORT = 9527       # UDP 发现端口
    WS_DEFAULT_PORT = 9528      # WebSocket 默认端口
    HEARTBEAT_INTERVAL = 5      # 心跳间隔 (秒)
    HEARTBEAT_TIMEOUT = 15      # 心跳超时 (秒)
    
    def __init__(
        self,
        node_name: str = "CoPaw-Node",
        host: str = "0.0.0.0",
        ws_port: int = WS_DEFAULT_PORT,
        enable_discovery: bool = True,
        node_id: Optional[str] = None,
    ):
        self.node_id = node_id or self._generate_node_id()
        self.node_name = node_name
        self.host = host
        self.ws_port = ws_port
        
        # 节点状态
        self.status = NodeStatus.IDLE
        self.capabilities = ["chat", "skill_execution", "task_processing"]
        
        # 连接管理
        self.known_nodes: Dict[str, NodeInfo] = {}  # 已知节点
        self.ws_connections: Dict[str, websockets.WebSocketClientProtocol] = {}  # 出站连接
        self.inbound_connections: Dict[str, websockets.WebSocketServerProtocol] = {}  # 入站连接
        
        # 任务管理
        self.pending_tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        
        # 消息回调
        self.message_callbacks: Dict[MessageType, List[Callable]] = {}
        
        # 运行状态
        self._running = False
        self._udp_socket: Optional[socket.socket] = None
        self._ws_server = None
        
        # 事件循环
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info(f"[{self.node_id}] 初始化完成 - {node_name}:{ws_port}")
    
    def _generate_node_id(self) -> str:
        """生成唯一节点 ID"""
        mac = self._get_mac_address()
        hostname = socket.gethostname()
        return hashlib.md5(f"{mac}:{hostname}:{time.time()}".encode()).hexdigest()[:12]
    
    def _get_mac_address(self) -> str:
        """获取 MAC 地址"""
        import uuid
        return ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0, 8*6, 8)][::-1])
    
    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    # ========== UDP 服务发现 ==========
    
    def _setup_udp_discovery(self):
        """设置 UDP 发现服务"""
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 绑定到发现端口
        try:
            self._udp_socket.bind(("", self.DISCOVERY_PORT))
        except OSError as e:
            logger.warning(f"UDP 端口 {self.DISCOVERY_PORT} 被占用：{e}")
            return False
        
        # 设置为非阻塞
        self._udp_socket.setblocking(False)
        return True
    
    def broadcast_discovery(self):
        """广播发现消息"""
        if not self._udp_socket:
            return
        
        message = json.dumps({
            "type": "discovery",
            "node_id": self.node_id,
            "node_name": self.node_name,
            "host": self._get_local_ip(),
            "ws_port": self.ws_port,
            "capabilities": self.capabilities,
            "timestamp": time.time(),
        }).encode('utf-8')
        
        # 广播到局域网
        broadcast_addr = "255.255.255.255"
        try:
            self._udp_socket.sendto(message, (broadcast_addr, self.DISCOVERY_PORT))
            logger.debug(f"[{self.node_id}] 发送发现广播 -> {broadcast_addr}")
        except Exception as e:
            logger.error(f"广播发送失败：{e}")
    
    async def _udp_listener(self):
        """UDP 监听线程"""
        logger.info(f"[{self.node_id}] UDP 发现服务启动 - 端口 {self.DISCOVERY_PORT}")
        
        while self._running:
            try:
                data, addr = self._udp_socket.recvfrom(4096)
                await self._handle_discovery_message(data, addr)
            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                if self._running:
                    logger.error(f"UDP 接收错误：{e}")
                await asyncio.sleep(1)
    
    async def _handle_discovery_message(self, data: bytes, addr: tuple):
        """处理发现消息"""
        try:
            message = json.loads(data.decode('utf-8'))
            msg_type = message.get("type")
            
            if msg_type == "discovery":
                # 收到其他节点的发现广播
                node_id = message.get("node_id")
                if node_id and node_id != self.node_id:
                    node_info = NodeInfo(
                        node_id=node_id,
                        host=message.get("host", addr[0]),
                        port=addr[1],
                        ws_port=message.get("ws_port", self.WS_DEFAULT_PORT),
                        name=message.get("node_name", "Unknown"),
                        capabilities=message.get("capabilities", []),
                        last_heartbeat=time.time(),
                    )
                    self.known_nodes[node_id] = node_info
                    logger.info(f"[{self.node_id}] 发现新节点：{node_info.name} ({node_info.host}:{node_info.ws_port})")
                    
                    # 响应发现
                    await self._send_discovery_response(addr)
                    
                    # 尝试建立 WebSocket 连接
                    await self._connect_to_node(node_info)
            
            elif msg_type == "discovery_resp":
                # 收到发现响应
                node_id = message.get("node_id")
                if node_id and node_id != self.node_id:
                    node_info = NodeInfo(
                        node_id=node_id,
                        host=message.get("host", addr[0]),
                        port=addr[1],
                        ws_port=message.get("ws_port", self.WS_DEFAULT_PORT),
                        name=message.get("node_name", "Unknown"),
                        capabilities=message.get("capabilities", []),
                        last_heartbeat=time.time(),
                    )
                    self.known_nodes[node_id] = node_info
                    
        except Exception as e:
            logger.error(f"处理发现消息失败：{e}")
    
    async def _send_discovery_response(self, addr: tuple):
        """发送发现响应"""
        response = json.dumps({
            "type": "discovery_resp",
            "node_id": self.node_id,
            "node_name": self.node_name,
            "host": self._get_local_ip(),
            "ws_port": self.ws_port,
            "capabilities": self.capabilities,
            "timestamp": time.time(),
        }).encode('utf-8')
        
        try:
            self._udp_socket.sendto(response, addr)
        except Exception as e:
            logger.error(f"发送发现响应失败：{e}")
    
    # ========== WebSocket 长连接 ==========
    
    async def start_websocket_server(self):
        """启动 WebSocket 服务器"""
        async def handler(websocket):
            await self._handle_websocket_connection(websocket)
        
        self._ws_server = await serve(
            handler,
            self.host,
            self.ws_port,
            ping_interval=20,
            ping_timeout=10,
        )
        
        logger.info(f"[{self.node_id}] WebSocket 服务器启动 - ws://{self._get_local_ip()}:{self.ws_port}")
    
    async def _handle_websocket_connection(self, websocket):
        """处理 WebSocket 连接"""
        node_id = None
        
        try:
            # 等待节点注册
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "register":
                        # 节点注册
                        node_id = data.get("node_id")
                        if node_id:
                            self.inbound_connections[node_id] = websocket
                            logger.info(f"[{self.node_id}] 节点 {node_id} 已连接 (入站)")
                            
                            # 发送确认
                            await websocket.send(json.dumps({
                                "type": "register_ack",
                                "node_id": self.node_id,
                                "status": "success",
                            }))
                    
                    elif msg_type == "heartbeat":
                        # 心跳
                        if node_id and node_id in self.known_nodes:
                            self.known_nodes[node_id].last_heartbeat = time.time()
                    
                    else:
                        # 其他消息类型
                        await self._handle_message(data, websocket)
                
                except json.JSONDecodeError:
                    logger.error(f"无效的 JSON 消息")
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.node_id}] 节点 {node_id} 断开连接")
        finally:
            if node_id and node_id in self.inbound_connections:
                del self.inbound_connections[node_id]
    
    async def _connect_to_node(self, node_info: NodeInfo):
        """连接到其他节点"""
        if node_info.node_id in self.ws_connections:
            return
        
        try:
            uri = f"ws://{node_info.host}:{node_info.ws_port}"
            websocket = await connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
            )
            
            # 发送注册消息
            await websocket.send(json.dumps({
                "type": "register",
                "node_id": self.node_id,
                "node_name": self.node_name,
                "capabilities": self.capabilities,
            }))
            
            # 等待确认
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            
            if data.get("type") == "register_ack" and data.get("status") == "success":
                self.ws_connections[node_info.node_id] = websocket
                self.known_nodes[node_info.node_id] = node_info
                logger.info(f"[{self.node_id}] 已连接到节点 {node_info.name} (出站)")
                
                # 启动消息接收
                asyncio.create_task(self._receive_messages(node_info.node_id, websocket))
            else:
                await websocket.close()
                
        except Exception as e:
            logger.error(f"[{self.node_id}] 连接节点 {node_info.host} 失败：{e}")
    
    async def _receive_messages(self, node_id: str, websocket):
        """接收消息"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data, websocket, node_id)
                except json.JSONDecodeError:
                    logger.error(f"无效的 JSON 消息")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.node_id}] 与节点 {node_id} 的连接断开")
        finally:
            if node_id in self.ws_connections:
                del self.ws_connections[node_id]
    
    async def _handle_message(self, data: dict, websocket, from_node_id: str = None):
        """处理收到的消息"""
        msg_type_str = data.get("type")
        
        try:
            msg_type = MessageType(msg_type_str)
        except ValueError:
            logger.warning(f"未知消息类型：{msg_type_str}")
            return
        
        # 调用回调
        callbacks = self.message_callbacks.get(msg_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data, from_node_id)
                else:
                    callback(data, from_node_id)
            except Exception as e:
                logger.error(f"消息回调执行失败：{e}")
        
        # 处理特定消息类型
        if msg_type == MessageType.TASK_REQUEST:
            await self._handle_task_request(data, websocket, from_node_id)
    
    # ========== 消息发送 ==========
    
    async def send_message(self, node_id: str, msg_type: MessageType, payload: dict):
        """发送消息到指定节点"""
        message = {
            "type": msg_type.value,
            "source_node": self.node_id,
            "target_node": node_id,
            "timestamp": time.time(),
            **payload,
        }
        
        # 通过出站连接发送
        if node_id in self.ws_connections:
            try:
                await self.ws_connections[node_id].send(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"发送消息到 {node_id} 失败：{e}")
                del self.ws_connections[node_id]
        
        # 通过入站连接发送
        elif node_id in self.inbound_connections:
            try:
                await self.inbound_connections[node_id].send(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"发送消息到 {node_id} 失败：{e}")
        
        logger.warning(f"找不到节点 {node_id} 的连接")
        return False
    
    async def broadcast_message(self, msg_type: MessageType, payload: dict, exclude_self: bool = True):
        """广播消息到所有节点"""
        tasks = []
        for node_id in list(self.ws_connections.keys()):
            if exclude_self and node_id == self.node_id:
                continue
            tasks.append(self.send_message(node_id, msg_type, payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    # ========== 任务调度 ==========
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"[{self.node_id}] 注册任务处理器：{task_type}")
    
    async def submit_task(self, task: Task, target_node: Optional[str] = None):
        """提交任务"""
        task.source_node = self.node_id
        
        if target_node:
            # 发送到指定节点
            success = await self.send_message(target_node, MessageType.TASK_REQUEST, {
                "task": asdict(task),
            })
            if success:
                self.pending_tasks[task.task_id] = task
        else:
            # 广播任务，寻找可用节点
            await self.broadcast_message(MessageType.TASK_REQUEST, {
                "task": asdict(task),
            })
            self.pending_tasks[task.task_id] = task
        
        return task.task_id
    
    async def _handle_task_request(self, data: dict, websocket, from_node_id: str):
        """处理任务请求"""
        task_data = data.get("task", {})
        task = Task(**task_data)
        
        logger.info(f"[{self.node_id}] 收到任务请求：{task.task_id} (类型：{task.task_type})")
        
        # 查找处理器
        handler = self.task_handlers.get(task.task_type)
        if not handler:
            await self._send_task_response(from_node_id, task.task_id, "failed", 
                                          error=f"不支持的任务类型：{task.task_type}")
            return
        
        try:
            # 执行任务
            self.status = NodeStatus.BUSY
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task)
            else:
                result = handler(task)
            
            await self._send_task_response(from_node_id, task.task_id, "completed", result=result)
            
        except Exception as e:
            logger.error(f"任务执行失败：{e}")
            await self._send_task_response(from_node_id, task.task_id, "failed", error=str(e))
        
        finally:
            self.status = NodeStatus.IDLE
    
    async def _send_task_response(self, target_node: str, task_id: str, status: str, 
                                  result: Any = None, error: str = None):
        """发送任务响应"""
        await self.send_message(target_node, MessageType.TASK_RESPONSE, {
            "task_id": task_id,
            "status": status,
            "result": result,
            "error": error,
        })
    
    # ========== 心跳保活 ==========
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                # 发送心跳到所有连接
                for node_id in list(self.ws_connections.keys()):
                    await self.send_message(node_id, MessageType.HEARTBEAT, {})
                
                # 检查超时节点
                current_time = time.time()
                timeout_nodes = []
                for node_id, node_info in self.known_nodes.items():
                    if current_time - node_info.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                        timeout_nodes.append(node_id)
                
                for node_id in timeout_nodes:
                    logger.warning(f"[{self.node_id}] 节点 {node_id} 心跳超时")
                    if node_id in self.ws_connections:
                        del self.ws_connections[node_id]
                    self.known_nodes[node_id].status = NodeStatus.OFFLINE.value
                
                # 定期广播发现
                self.broadcast_discovery()
                
            except Exception as e:
                logger.error(f"心跳循环错误：{e}")
            
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
    
    # ========== 启动与停止 ==========
    
    async def start(self):
        """启动网络服务"""
        self._running = True
        self._loop = asyncio.get_event_loop()
        
        # 启动 UDP 发现
        if self._setup_udp_discovery():
            asyncio.create_task(self._udp_listener())
        
        # 启动 WebSocket 服务器
        await self.start_websocket_server()
        
        # 启动心跳循环
        asyncio.create_task(self._heartbeat_loop())
        
        # 发送初始发现广播
        self.broadcast_discovery()
        
        logger.info(f"[{self.node_id}] 网络服务启动完成")
    
    async def stop(self):
        """停止网络服务"""
        self._running = False
        
        # 关闭所有连接
        for ws in list(self.ws_connections.values()):
            await ws.close()
        for ws in list(self.inbound_connections.values()):
            await ws.close()
        
        # 关闭服务器
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
        
        # 关闭 UDP socket
        if self._udp_socket:
            self._udp_socket.close()
        
        logger.info(f"[{self.node_id}] 网络服务已停止")
    
    def get_status(self) -> dict:
        """获取节点状态"""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "host": self._get_local_ip(),
            "ws_port": self.ws_port,
            "status": self.status.value,
            "known_nodes": len(self.known_nodes),
            "active_connections": len(self.ws_connections) + len(self.inbound_connections),
            "pending_tasks": len(self.pending_tasks),
        }


# ========== 全局实例 ==========

_lan_network: Optional[LANMeshNetwork] = None


def get_lan_network() -> Optional[LANMeshNetwork]:
    """获取全局 LAN 网络实例"""
    return _lan_network


def init_lan_network(
    node_name: str = "CoPaw-Node",
    ws_port: int = LANMeshNetwork.WS_DEFAULT_PORT,
    **kwargs
) -> LANMeshNetwork:
    """初始化全局 LAN 网络实例"""
    global _lan_network
    _lan_network = LANMeshNetwork(node_name=node_name, ws_port=ws_port, **kwargs)
    return _lan_network


async def start_lan_network():
    """启动全局 LAN 网络"""
    if _lan_network:
        await _lan_network.start()


async def stop_lan_network():
    """停止全局 LAN 网络"""
    if _lan_network:
        await _lan_network.stop()
