# 📈 A 股市场数据报告

基于 Vue 3 + ECharts 的 A 股市场数据可视化系统。

## 🌐 在线访问

**https://huangrichao.gitee.io/stock_report/**

## 📊 功能特性

- 📈 **市场统计** - 成交额、涨跌家数、涨停跌停统计
- 📉 **指数行情** - 上证指数、深证成指、创业板指等
- 📊 **K 线图** - 指数历史走势（ECharts 渲染）
- 📊 **涨跌分布** - 全市场涨跌幅分布柱状图
- 🔥 **热门板块** - 板块涨幅排名、龙一龙二、封板时间
- 🏆 **涨停股** - 涨停股 TOP20、连板统计

## 🚀 快速部署

```bash
# 1. 克隆仓库
git clone https://gitee.com/huangrichao/stock_report.git

# 2. 进入目录
cd stock_report

# 3. 启动本地服务
python3 -m http.server 8080

# 4. 访问
打开浏览器：http://localhost:8080
```

## 📁 文件说明

```
stock_report/
├── index.html      # 主页面（Vue 3 + ECharts）
├── api_data.json   # 市场数据（每日更新）
├── DEPLOY.md       # 部署指南
└── push.sh         # 一键推送脚本
```

## 🔄 数据更新

每日收盘后更新 `api_data.json`：

```bash
# 手动更新
cd /Users/tingchi/stock_report
./push.sh

# 或自动更新（添加定时任务）
crontab -e
# 每个交易日 17:00 更新
0 17 * * 1-5 cd /Users/tingchi/stock_report && ./push.sh
```

## 💻 技术栈

- **前端**: Vue 3 (CDN)
- **图表**: ECharts 5.4
- **数据**: Tushare Pro / Finnhub / NewsAPI
- **部署**: Gitee Pages

## 📊 数据示例

```json
{
  "trade_date": "2026-03-06",
  "market_stats": {
    "total_amount": 2.15,
    "up": 3200,
    "down": 1800,
    "limit_up": 110,
    "sentiment": 64.0
  },
  "today_sectors": [...],
  "top_stocks": [...]
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**维护者**: 小超 🦞  
**最后更新**: 2026-03-09
