# MIA System Monitoring Setup Guide

**白皮书依据**: 第十三章 13.3 Grafana 仪表板配置

本目录包含 MIA 系统的监控配置文件，用于 Prometheus 指标采集和 Grafana 可视化。

## 文件说明

- `grafana_dashboard.json` - Grafana 仪表板配置（8个核心面板）
- `prometheus.yml` - Prometheus 采集配置
- `alert_rules.yml` - Prometheus 告警规则（12条规则）
- `README.md` - 本文档

## 快速开始

### 1. 安装 Prometheus

#### Windows 安装步骤

```bash
# 1. 下载 Prometheus
# 访问: https://prometheus.io/download/
# 下载: prometheus-2.x.x.windows-amd64.zip

# 2. 解压到工具目录
# 解压到: D:/MIA_Tools/prometheus/

# 3. 复制配置文件
copy monitoring\prometheus.yml D:\MIA_Tools\prometheus\
copy monitoring\alert_rules.yml D:\MIA_Tools\prometheus\

# 4. 启动 Prometheus
cd D:\MIA_Tools\prometheus\
prometheus.exe --config.file=prometheus.yml
```

Prometheus 将在 `http://localhost:9090` 启动。

### 2. 安装 Grafana

#### Windows 安装步骤

```bash
# 1. 下载 Grafana
# 访问: https://grafana.com/grafana/download
# 下载: grafana-x.x.x.windows-amd64.zip

# 2. 解压到工具目录
# 解压到: D:/MIA_Tools/grafana/

# 3. 启动 Grafana
cd D:\MIA_Tools\grafana\bin\
grafana-server.exe
```

Grafana 将在 `http://localhost:3000` 启动。

### 3. 配置 Grafana

1. **访问 Grafana**
   - 打开浏览器访问: `http://localhost:3000`
   - 默认账号: `admin`
   - 默认密码: `admin`
   - 首次登录后会要求修改密码

2. **添加 Prometheus 数据源**
   - 点击左侧菜单 "Configuration" → "Data Sources"
   - 点击 "Add data source"
   - 选择 "Prometheus"
   - 配置:
     - Name: `Prometheus`
     - URL: `http://localhost:9090`
     - Access: `Server (default)`
   - 点击 "Save & Test"

3. **导入仪表板**
   - 点击左侧菜单 "+" → "Import"
   - 点击 "Upload JSON file"
   - 选择 `monitoring/grafana_dashboard.json`
   - 选择数据源: `Prometheus`
   - 点击 "Import"

## 仪表板面板说明

### 面板 1: Soldier Mode
- **类型**: Stat（状态指标）
- **指标**: `mia_soldier_mode`
- **说明**: 显示当前 Soldier 执行模式
  - `0` = Local（本地 AMD GPU）
  - `1` = Cloud（云端 API）
- **颜色**:
  - 绿色 = Local（正常）
  - 黄色 = Cloud（降级）

### 面板 2: Soldier Latency P99
- **类型**: Time Series（时间序列）
- **指标**: `histogram_quantile(0.99, rate(mia_soldier_latency_seconds_bucket[5m]))`
- **说明**: Soldier 决策延迟的 99 分位数
- **目标**: < 150ms
- **阈值**:
  - 绿色: < 150ms
  - 红色: ≥ 150ms

### 面板 3: Trade Volume (5m)
- **类型**: Time Series（柱状图）
- **指标**: `rate(mia_trades_total[5m]) * 300`
- **说明**: 每5分钟的交易量，按策略分组

### 面板 4: Daily PnL
- **类型**: Stat（状态指标）
- **指标**: `mia_portfolio_pnl{period='daily'}`
- **说明**: 当日盈亏
- **单位**: CNY（人民币）
- **颜色**:
  - 红色: 亏损
  - 黄色: 盈亏平衡
  - 绿色: 盈利

### 面板 5: Portfolio Value
- **类型**: Time Series（时间序列）
- **指标**: `mia_portfolio_value`
- **说明**: 账户总资产价值
- **单位**: CNY（人民币）

### 面板 6: GPU Memory Usage
- **类型**: Time Series（时间序列）
- **指标**: `mia_gpu_memory_used_bytes / mia_gpu_memory_total_bytes * 100`
- **说明**: GPU 显存使用率
- **单位**: %
- **阈值**:
  - 绿色: < 80%
  - 黄色: 80-90%
  - 红色: > 90%

### 面板 7: System Resources
- **类型**: Time Series（时间序列）
- **指标**:
  - `mia_system_cpu_percent` - CPU 使用率
  - `mia_system_memory_percent` - 内存使用率
  - `mia_system_disk_percent{drive='D:'}` - D盘使用率
- **说明**: 系统资源使用情况
- **单位**: %
- **阈值**:
  - 绿色: < 80%
  - 黄色: 80-90%
  - 红色: > 90%

### 面板 8: Redis Latency
- **类型**: Time Series（时间序列）
- **指标**: `rate(mia_redis_latency_seconds_sum[5m]) / rate(mia_redis_latency_seconds_count[5m])`
- **说明**: Redis 操作平均延迟，按操作类型分组
- **单位**: ms
- **阈值**:
  - 绿色: < 10ms
  - 黄色: 10-50ms
  - 红色: > 50ms

## 告警规则说明

系统配置了 12 条告警规则，覆盖以下场景：

### 紧急告警（Emergency）
1. **RedisDown**: Redis 连接失败超过 30 秒
2. **CriticalLoss**: 日亏损超过账户总值的 10%

### 严重告警（Critical）
3. **SoldierDegraded**: Soldier 在 Cloud 模式运行超过 10 分钟
4. **GPUOverheating**: GPU 温度超过 85°C 持续 2 分钟
5. **DailyLossExceeded**: 日亏损超过账户总值的 5%
6. **HealthCheckFailed**: 健康检查 API 无响应超过 1 分钟

### 警告告警（Warning）
7. **HighMemoryUsage**: 内存使用率超过 90% 持续 5 分钟
8. **LowDiskSpace**: D盘使用率超过 90% 持续 5 分钟
9. **SoldierHighLatency**: Soldier P99 延迟超过 150ms 持续 5 分钟
10. **RedisHighLatency**: Redis 平均延迟超过 50ms 持续 5 分钟
11. **GPUMemoryHigh**: GPU 显存使用率超过 90% 持续 5 分钟
12. **TradeVolumeAnomaly**: 交易量异常下降（低于1小时前的10%）

## 告警路由

告警将根据严重程度自动路由到不同渠道：

| 严重程度 | 路由渠道 | 响应时间 |
|---------|---------|---------|
| Emergency | 电话 + 微信 | 立即 |
| Critical | 微信 | 5分钟内 |
| Warning | 微信（仅工作时间） | 10分钟内 |
| Info | 日志 | - |

## 性能要求

根据白皮书第十三章要求：

- **指标采集间隔**: 10秒
- **告警评估间隔**: 10秒
- **Prometheus 端口**: 9090
- **Grafana 端口**: 3000
- **健康检查 API 端口**: 8000

## 故障排查

### Prometheus 无法启动

1. 检查端口 9090 是否被占用:
   ```bash
   netstat -ano | findstr :9090
   ```

2. 检查配置文件语法:
   ```bash
   prometheus.exe --config.file=prometheus.yml --check-config
   ```

3. 查看日志:
   ```bash
   # Prometheus 日志会输出到控制台
   ```

### Grafana 无法连接 Prometheus

1. 确认 Prometheus 正在运行:
   - 访问 `http://localhost:9090`
   - 检查 "Status" → "Targets"

2. 检查数据源配置:
   - Grafana → Configuration → Data Sources
   - 点击 "Test" 按钮

3. 检查防火墙设置:
   - 确保 9090 端口未被防火墙阻止

### 仪表板无数据

1. 确认 MIA 系统正在运行并暴露指标:
   ```bash
   # 检查指标端点
   curl http://localhost:9090/metrics
   ```

2. 检查 Prometheus 是否成功采集指标:
   - 访问 `http://localhost:9090/targets`
   - 确认所有 target 状态为 "UP"

3. 检查指标名称是否正确:
   - 在 Prometheus 中执行查询: `mia_soldier_mode`
   - 确认有数据返回

## 维护建议

### 数据保留

Prometheus 默认保留 15 天的数据。如需调整:

```bash
prometheus.exe --config.file=prometheus.yml --storage.tsdb.retention.time=30d
```

### 备份

定期备份以下目录:
- Prometheus 数据: `D:/MIA_Tools/prometheus/data/`
- Grafana 配置: `D:/MIA_Tools/grafana/data/`

### 监控 Prometheus 自身

Prometheus 会自动监控自身性能，可在仪表板中添加以下指标:
- `prometheus_tsdb_head_samples` - 内存中的样本数
- `prometheus_tsdb_head_series` - 时间序列数
- `prometheus_http_requests_total` - HTTP 请求总数

## 参考资料

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- MIA 白皮书: 第十三章 监控与可观测性

## 支持

如有问题，请参考:
1. MIA 白皮书第十三章
2. `00_核心文档/DEVELOPMENT_GUIDE.md`
3. 项目 Issue 跟踪系统
