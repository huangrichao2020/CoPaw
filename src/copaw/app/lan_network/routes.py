# -*- coding: utf-8 -*-
"""
局域网分布式智能体 API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from . import (
    get_lan_network,
    init_lan_network,
    start_lan_network,
    stop_lan_network,
    LANMeshNetwork,
    Task,
)

router = APIRouter(prefix="/api/lan", tags=["lan-network"])


class NodeConfig(BaseModel):
    """节点配置"""
    node_name: str = "CoPaw-Node"
    ws_port: int = 9528
    enable_discovery: bool = True


class NodeStatusResponse(BaseModel):
    """节点状态响应"""
    node_id: str
    node_name: str
    host: str
    ws_port: int
    status: str
    known_nodes: int
    active_connections: int
    pending_tasks: int


class NetworkNode(BaseModel):
    """网络节点信息"""
    node_id: str
    host: str
    ws_port: int
    name: str
    status: str
    capabilities: List[str]


@router.post("/init")
async def init_network(config: NodeConfig):
    """初始化局域网网络"""
    try:
        network = init_lan_network(
            node_name=config.node_name,
            ws_port=config.ws_port,
            enable_discovery=config.enable_discovery,
        )
        return {"status": "success", "node_id": network.node_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_network():
    """启动局域网网络"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="请先初始化网络")
    
    try:
        asyncio.create_task(network.start())
        return {"status": "success", "message": "网络启动中"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_network():
    """停止局域网网络"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    try:
        await network.stop()
        return {"status": "success", "message": "网络已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=NodeStatusResponse)
async def get_network_status():
    """获取网络状态"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    status = network.get_status()
    return NodeStatusResponse(**status)


@router.get("/nodes", response_model=List[NetworkNode])
async def get_known_nodes():
    """获取已知节点列表"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    nodes = []
    for node_id, node_info in network.known_nodes.items():
        nodes.append(NetworkNode(
            node_id=node_info.node_id,
            host=node_info.host,
            ws_port=node_info.ws_port,
            name=node_info.name,
            status=node_info.status,
            capabilities=node_info.capabilities,
        ))
    
    return nodes


@router.post("/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """广播消息"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    from . import MessageType
    msg_type = MessageType(message.get("type", "broadcast"))
    payload = message.get("payload", {})
    
    await network.broadcast_message(msg_type, payload)
    return {"status": "success"}


@router.post("/task/submit")
async def submit_task(task_data: Dict[str, Any], target_node: Optional[str] = None):
    """提交任务"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    task = Task(
        task_id=task_data.get("task_id"),
        task_type=task_data.get("task_type"),
        payload=task_data.get("payload", {}),
        source_node=network.node_id,
        target_node=target_node,
    )
    
    task_id = await network.submit_task(task, target_node)
    return {"status": "success", "task_id": task_id}


@router.post("/task/handler/register")
async def register_task_handler(task_type: str):
    """注册任务处理器（示例）"""
    network = get_lan_network()
    if not network:
        raise HTTPException(status_code=400, detail="网络未初始化")
    
    # 示例处理器
    async def example_handler(task: Task):
        return {"processed": True, "task_id": task.task_id}
    
    network.register_task_handler(task_type, example_handler)
    return {"status": "success", "task_type": task_type}
