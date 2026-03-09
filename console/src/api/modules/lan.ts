import { request } from "../request";

export interface NodeConfig {
  node_name: string;
  ws_port: number;
  enable_discovery: boolean;
}

export interface NetworkStatus {
  node_id: string;
  node_name: string;
  host: string;
  ws_port: number;
  status: string;
  known_nodes: number;
  active_connections: number;
  pending_tasks: number;
}

export interface NetworkNode {
  node_id: string;
  host: string;
  ws_port: number;
  name: string;
  status: string;
  capabilities: string[];
}

async function get<T = unknown>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

async function post<T = unknown>(path: string, data?: any): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}

export const lanApi = {
  /** 初始化网络 */
  initNetwork: (config: NodeConfig) =>
    post("/api/lan/init", config),

  /** 启动网络 */
  startNetwork: () =>
    post("/api/lan/start"),

  /** 停止网络 */
  stopNetwork: () =>
    post("/api/lan/stop"),

  /** 获取网络状态 */
  getNetworkStatus: () =>
    get<NetworkStatus>("/api/lan/status"),

  /** 获取节点列表 */
  getNetworkNodes: () =>
    get<NetworkNode[]>("/api/lan/nodes"),

  /** 广播消息 */
  broadcastMessage: (message: any) =>
    post("/api/lan/broadcast", message),

  /** 提交任务 */
  submitTask: (task: any, target_node?: string) =>
    post(`/api/lan/task/submit${target_node ? `?target_node=${target_node}` : ""}`, task),

  /** 注册任务处理器 */
  registerTaskHandler: (task_type: string) =>
    post(`/api/lan/task/handler/register?task_type=${task_type}`),
};
