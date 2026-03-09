import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  Table,
  Tag,
  message,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Space,
  Statistic,
  Row,
  Col,
  Badge,
} from "antd";
import {
  Network,
  Server,
  Wifi,
  RefreshCw,
  Play,
  Square,
  Settings,
} from "lucide-react";
import api from "../../../api";
import styles from "./index.module.less";

interface NodeInfo {
  node_id: string;
  host: string;
  ws_port: number;
  name: string;
  status: string;
  capabilities: string[];
}

interface NetworkStatus {
  node_id: string;
  node_name: string;
  host: string;
  ws_port: number;
  status: string;
  known_nodes: number;
  active_connections: number;
  pending_tasks: number;
}

function LANNetworkPage() {
  useTranslation();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<NetworkStatus | null>(null);
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [initialized, setInitialized] = useState(false);
  const [running, setRunning] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await api.getNetworkStatus();
      setStatus(res);
      setInitialized(true);
    } catch (error: any) {
      if (error.response?.status === 400) {
        setInitialized(false);
      }
    }
  };

  const fetchNodes = async () => {
    try {
      const res = await api.getNetworkNodes();
      setNodes(res);
    } catch (error) {
      console.error("Failed to fetch nodes:", error);
    }
  };

  const handleInit = async (values: any) => {
    setLoading(true);
    try {
      await api.initNetwork(values);
      setInitialized(true);
      message.success("网络初始化成功");
      setConfigModalOpen(false);
      fetchStatus();
    } catch (error: any) {
      message.error(`初始化失败：${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      await api.startNetwork();
      setRunning(true);
      message.success("网络启动成功");
      fetchStatus();
    } catch (error: any) {
      message.error(`启动失败：${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await api.stopNetwork();
      setRunning(false);
      message.success("网络已停止");
      fetchStatus();
    } catch (error: any) {
      message.error(`停止失败：${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    fetchStatus();
    fetchNodes();
  };

  useEffect(() => {
    fetchStatus();
    fetchNodes();
    
    // 定时刷新
    const interval = setInterval(() => {
      if (initialized && running) {
        fetchStatus();
        fetchNodes();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [initialized, running]);

  const nodeColumns = [
    {
      title: "节点 ID",
      dataIndex: "node_id",
      key: "node_id",
      width: 150,
    },
    {
      title: "节点名称",
      dataIndex: "name",
      key: "name",
      width: 150,
    },
    {
      title: "主机地址",
      dataIndex: "host",
      key: "host",
      width: 160,
      render: (host: string, record: NodeInfo) => `${host}:${record.ws_port}`,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: string) => (
        <Badge
          status={status === "online" || status === "idle" ? "success" : "error"}
          text={status.toUpperCase()}
        />
      ),
    },
    {
      title: "能力",
      dataIndex: "capabilities",
      key: "capabilities",
      render: (capabilities: string[]) => (
        <Space size={4}>
          {capabilities.slice(0, 3).map((cap) => (
            <Tag key={cap} color="blue">{cap}</Tag>
          ))}
          {capabilities.length > 3 && (
            <Tag color="gray">+{capabilities.length - 3}</Tag>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.lanNetworkPage}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.title}>
            <Network size={24} style={{ marginRight: 12 }} />
            局域网分布式智能体
          </h1>
          <p className={styles.description}>
            管理局域网内的 CoPaw 节点，实现分布式任务调度与协作
          </p>
        </div>
        <Space>
          <Button icon={<RefreshCw size={16} />} onClick={handleRefresh}>
            刷新
          </Button>
          {!initialized ? (
            <Button
              type="primary"
              icon={<Settings size={16} />}
              onClick={() => setConfigModalOpen(true)}
            >
              初始化网络
            </Button>
          ) : (
            <>
              {!running ? (
                <Button
                  type="primary"
                  icon={<Play size={16} />}
                  onClick={handleStart}
                  loading={loading}
                >
                  启动网络
                </Button>
              ) : (
                <Button
                  danger
                  icon={<Square size={16} />}
                  onClick={handleStop}
                  loading={loading}
                >
                  停止网络
                </Button>
              )}
              <Button
                icon={<Settings size={16} />}
                onClick={() => setConfigModalOpen(true)}
              >
                配置
              </Button>
            </>
          )}
        </Space>
      </div>

      {!initialized ? (
        <Card className={styles.emptyCard}>
          <div className={styles.emptyState}>
            <Network size={64} strokeWidth={1} />
            <h3>尚未初始化局域网网络</h3>
            <p>点击"初始化网络"按钮开始配置</p>
          </div>
        </Card>
      ) : (
        <>
          {/* 状态统计 */}
          {status && (
            <Row gutter={16} className={styles.statsRow}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="节点 ID"
                    value={status.node_id}
                    valueStyle={{ fontSize: 14 }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="当前状态"
                    value={status.status.toUpperCase()}
                    valueStyle={{
                      color: status.status === "idle" ? "#52c41a" : "#1890ff",
                    }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="已知节点"
                    value={status.known_nodes}
                    suffix="个"
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="活跃连接"
                    value={status.active_connections}
                    suffix="个"
                  />
                </Card>
              </Col>
            </Row>
          )}

          {/* 节点列表 */}
          <Card
            title={
              <Space>
                <Server size={18} />
                网络节点
              </Space>
            }
            extra={
              <Tag color="green" icon={<Wifi size={14} />}>
                {running ? "运行中" : "已停止"}
              </Tag>
            }
            className={styles.nodesCard}
          >
            <Table
              columns={nodeColumns}
              dataSource={nodes}
              rowKey="node_id"
              pagination={false}
              loading={loading}
              locale={{ emptyText: "暂无发现其他节点" }}
            />
          </Card>

          {/* 使用说明 */}
          <Card title="使用说明" className={styles.helpCard}>
            <div className={styles.helpContent}>
              <h4>🚀 快速开始</h4>
              <ol>
                <li>在每台设备上安装 CoPaw</li>
                <li>确保所有设备在同一局域网内</li>
                <li>分别在各设备上点击"启动网络"</li>
                <li>系统会自动发现并连接其他节点</li>
              </ol>

              <h4>📡 通信原理</h4>
              <ul>
                <li><strong>UDP 广播</strong>：自动发现局域网内的其他 CoPaw 节点</li>
                <li><strong>WebSocket</strong>：节点间建立持久化长连接</li>
                <li><strong>心跳机制</strong>：5 秒心跳，15 秒超时检测</li>
                <li><strong>任务调度</strong>：支持分布式任务分配与执行</li>
              </ul>

              <h4>🔧 配置说明</h4>
              <ul>
                <li><strong>节点名称</strong>：用于标识当前设备</li>
                <li><strong>WebSocket 端口</strong>：默认 9528，确保防火墙允许</li>
                <li><strong>服务发现</strong>：启用 UDP 广播发现</li>
              </ul>
            </div>
          </Card>
        </>
      )}

      {/* 配置弹窗 */}
      <Modal
        title="局域网网络配置"
        open={configModalOpen}
        onCancel={() => setConfigModalOpen(false)}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleInit}
          initialValues={{
            node_name: `CoPaw-${navigator.platform.includes("Mac") ? "Mac" : "PC"}`,
            ws_port: 9528,
            enable_discovery: true,
          }}
        >
          <Form.Item
            name="node_name"
            label="节点名称"
            rules={[{ required: true, message: "请输入节点名称" }]}
          >
            <Input placeholder="例如：CoPaw-Mac-Office" />
          </Form.Item>

          <Form.Item
            name="ws_port"
            label="WebSocket 端口"
            rules={[{ required: true, message: "请输入端口号" }]}
          >
            <InputNumber min={1024} max={65535} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item
            name="enable_discovery"
            label="服务发现"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                初始化
              </Button>
              <Button onClick={() => setConfigModalOpen(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default LANNetworkPage;
