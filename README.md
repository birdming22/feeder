# feeder

## 模組架構規劃

### 1. 整體架構圖

```
network_monitor/
├── main.py                 # 主程式入口
├── config/
│   ├── __init__.py
│   ├── config_manager.py   # 配置管理模組
│   └── default_config.json # 預設配置檔案
├── network/
│   ├── __init__.py
│   ├── interface_manager.py # 網卡管理模組
│   ├── latency_monitor.py   # 延遲監控模組
│   ├── packet_loss_monitor.py # 封包遺失監控模組
│   └── throughput_monitor.py  # 吞吐量監控模組
├── data/
│   ├── __init__.py
│   ├── data_collector.py   # 資料收集器
│   └── data_formatter.py   # 資料格式化器
├── transmission/
│   ├── __init__.py
│   └── udp_sender.py       # UDP傳輸模組
├── utils/
│   ├── __init__.py
│   ├── logger.py           # 日誌模組
│   └── exceptions.py       # 自定義例外
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_network.py
    └── test_transmission.py
```

### 2. 核心模組詳細設計

#### 2.1 配置管理模組 (`config/config_manager.py`)
```
職責：
- 讀取和解析JSON配置檔案
- 提供配置驗證功能
- 支援配置熱重載

主要類別：
- ConfigManager: 配置管理主類別
- ConfigValidator: 配置驗證器

主要方法：
- load_config(file_path)
- validate_config(config_dict)
- get_config_value(key_path)
- reload_config()
```

#### 2.2 網卡管理模組 (`network/interface_manager.py`)
```
職責：
- 偵測和管理網路介面
- 提供網卡基本資訊
- 跨平台網卡名稱處理

主要類別：
- NetworkInterface: 網卡資訊封裝
- InterfaceManager: 網卡管理器

主要方法：
- get_available_interfaces()
- get_interface_by_name(name)
- get_interface_stats(interface)
- is_interface_active(interface)
```

#### 2.3 效能監控模組群

**延遲監控 (`network/latency_monitor.py`)**
```
職責：
- 執行ping測試
- 計算平均延遲、最小/最大延遲
- 支援多目標測試

主要類別：
- LatencyMonitor

主要方法：
- ping_host(target_ip, count, timeout)
- get_latency_stats()
- continuous_monitor(interval)
```

**封包遺失監控 (`network/packet_loss_monitor.py`)**
```
職責：
- 監控封包遺失率
- 統計遺失封包數量和百分比
- 長期趨勢分析

主要類別：
- PacketLossMonitor

主要方法：
- measure_packet_loss(target_ip, count)
- get_loss_statistics()
- reset_statistics()
```

**吞吐量監控 (`network/throughput_monitor.py`)**
```
職責：
- 監控網卡流量統計
- 計算即時吞吐量
- 區分上傳/下載速率

主要類別：
- ThroughputMonitor

主要方法：
- get_interface_throughput(interface)
- calculate_speed(time_interval)
- get_bandwidth_utilization()
```

#### 2.4 資料處理模組群

**資料收集器 (`data/data_collector.py`)**
```
職責：
- 協調各監控模組收集資料
- 統一資料收集排程
- 資料暫存和批次處理

主要類別：
- DataCollector
- CollectionScheduler

主要方法：
- collect_all_metrics()
- schedule_collection(interval)
- get_cached_data()
```

**資料格式化器 (`data/data_formatter.py`)**
```
職責：
- 將監控資料格式化為JSON
- 資料結構標準化
- 時間戳記管理

主要類別：
- DataFormatter

主要方法：
- format_to_json(raw_data)
- add_timestamp(data)
- validate_json_structure(json_data)
```

#### 2.5 傳輸模組 (`transmission/udp_sender.py`)
```
職責：
- UDP封包傳送
- 連線管理和重試機制
- 傳送狀態監控

主要類別：
- UDPSender
- ConnectionManager

主要方法：
- send_data(json_data, target_ip, target_port)
- setup_connection()
- handle_send_failure()
```

#### 2.6 工具模組群

**日誌模組 (`utils/logger.py`)**
```
職責：
- 統一日誌記錄
- 多層級日誌支援
- 日誌輪替管理

主要類別：
- Logger

主要方法：
- setup_logger(name, level, file_path)
- log_performance_data(data)
- log_error(exception)
```

**自定義例外 (`utils/exceptions.py`)**
```
職責：
- 定義專案特定例外
- 錯誤分類和處理

例外類別：
- ConfigError: 配置相關錯誤
- NetworkInterfaceError: 網卡相關錯誤
- MonitoringError: 監控功能錯誤
- TransmissionError: 傳輸相關錯誤
```

### 3. 主程式流程 (`main.py`)

```
主要功能：
1. 初始化配置管理器
2. 創建並配置各監控模組
3. 啟動資料收集排程器
4. 處理資料格式化和傳送
5. 錯誤處理和優雅關閉

主要類別：
- NetworkMonitorApp: 主應用程式類別

執行流程：
startup() → load_config() → initialize_monitors() → 
start_collection() → main_loop() → shutdown()
```

### 4. 模組間依賴關係

```
main.py
├── config.config_manager
├── data.data_collector
│   ├── network.interface_manager
│   ├── network.latency_monitor
│   ├── network.packet_loss_monitor
│   └── network.throughput_monitor
├── data.data_formatter
├── transmission.udp_sender
└── utils.logger, utils.exceptions
```

### 5. 配置檔案結構 (`config/default_config.json`)

```json
{
  "network": {
    "interface": "eth0",
    "targets": ["8.8.8.8", "1.1.1.1"]
  },
  "monitoring": {
    "interval": 60,
    "latency_samples": 10,
    "throughput_window": 30
  },
  "transmission": {
    "udp_server": {
      "ip": "192.168.1.100",
      "port": 8080
    },
    "retry_attempts": 3,
    "timeout": 5
  },
  "logging": {
    "level": "INFO",
    "file": "network_monitor.log"
  }
}
```

### 6. 實作優先級建議

**Phase 1: 基礎架構**
1. utils模組（logger, exceptions）
2. config模組
3. 基本的main.py框架

**Phase 2: 核心功能**
4. network.interface_manager
5. network.latency_monitor
6. data模組群

**Phase 3: 完整功能**
7. network.packet_loss_monitor
8. transmission.udp_sender
9. network.throughput_monitor（最複雜）

**Phase 4: 整合與測試**
10. 整合測試
11. 錯誤處理完善
12. 效能優化
