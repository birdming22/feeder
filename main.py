#!/usr/bin/env python3
"""
網路效能監控主程式
整合現有的ping_monitor和runtime_var，使用獨立的執行緒管理器
"""

import json
import time
import signal
import sys
from thread_manager import ThreadManager

# 假設你有這些現成的模組
# from your_existing_modules import RuntimeVar, PingMonitor


class SimpleRuntimeVar:
    """簡單的runtime_var實現（如果你沒有現成的話）"""
    
    def __init__(self):
        self._data = {}
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def set(self, key, value):
        self._data[key] = value
        
    def update(self, updates):
        self._data.update(updates)


class SimplePingMonitor:
    """簡單的ping_monitor實現（如果你沒有現成的話）"""
    
    def __init__(self):
        pass
    
    def get_ping_stats(self, target, count=5):
        """獲取ping統計資料"""
        import subprocess
        import os
        
        try:
            # 構建ping指令
            ping_cmd = ["ping", "-c", str(count), target]
            if os.name == 'nt':  # Windows
                ping_cmd = ["ping", "-n", str(count), target]
            
            result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return self._parse_ping_output(result.stdout, os.name == 'nt')
            else:
                return {"latency": -1, "packet_loss": 100}
                
        except Exception as e:
            print(f"Ping錯誤: {e}")
            return {"latency": -1, "packet_loss": 100}
    
    def _parse_ping_output(self, output, is_windows):
        """解析ping輸出"""
        latency = -1
        packet_loss = 100
        
        try:
            lines = output.split('\n')
            
            if is_windows:
                for line in lines:
                    if "Average" in line:
                        latency = float(line.split('=')[-1].replace('ms', '').strip())
                    elif "Lost" in line:
                        lost_part = line.split('(')[1].split('%')[0]
                        packet_loss = float(lost_part)
            else:
                for line in lines:
                    if "avg" in line:
                        parts = line.split('/')
                        if len(parts) >= 4:
                            latency = float(parts[-2])
                    elif "packet loss" in line:
                        packet_loss = float(line.split('%')[0].split()[-1])
        except:
            pass
        
        return {"latency": latency, "packet_loss": packet_loss}


class NetworkMonitorApp:
    """網路監控應用程式主類別"""
    
    def __init__(self, config_file="config.json"):
        """初始化應用程式"""
        self.config = self.load_config(config_file)
        
        # 初始化你現有的模組
        # self.runtime_var = RuntimeVar()  # 使用你現有的
        # self.ping_monitor = PingMonitor()  # 使用你現有的
        
        # 如果沒有現成的，使用簡單實現
        self.runtime_var = SimpleRuntimeVar()
        self.ping_monitor = SimplePingMonitor()
        
        # 初始化執行緒管理器
        self.thread_manager = ThreadManager(
            config=self.config,
            runtime_var=self.runtime_var,
            ping_monitor=self.ping_monitor
        )
        
        # 設定信號處理
        self.setup_signal_handlers()
    
    def load_config(self, config_file):
        """載入配置檔案"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置檔案 {config_file} 不存在，創建預設配置...")
            config = self.get_default_config()
            self.save_config(config, config_file)
            return config
        except Exception as e:
            print(f"載入配置錯誤: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """獲取預設配置"""
        return {
            "interface": "eth0",
            "target_ip": "8.8.8.8",
            "ping_interval": 30,
            "ping_count": 5,
            "network_monitor_interval": 10,
            "report_interval": 60,
            "udp_server": {
                "ip": "127.0.0.1",
                "port": 8080
            }
        }
    
    def save_config(self, config, config_file):
        """儲存配置檔案"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"配置已儲存至 {config_file}")
        except Exception as e:
            print(f"儲存配置錯誤: {e}")
    
    def setup_signal_handlers(self):
        """設定信號處理器"""
        def signal_handler(signum, frame):
            print(f"\n收到信號 {signum}，正在關閉程式...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """啟動應用程式"""
        print("=== 網路效能監控系統 ===")
        print(f"目標IP: {self.config['target_ip']}")
        print(f"監控網卡: {self.config['interface']}")
        print(f"UDP伺服器: {self.config['udp_server']['ip']}:{self.config['udp_server']['port']}")
        print(f"Ping間隔: {self.config['ping_interval']}秒")
        print(f"網路監控間隔: {self.config['network_monitor_interval']}秒")
        print(f"報告間隔: {self.config['report_interval']}秒")
        print("按Ctrl+C停止監控")
        print("=" * 30)
        
        # 啟動所有執行緒
        self.thread_manager.start_all_threads()
        
        # 主迴圈 - 監控狀態
        try:
            self.main_loop()
        except KeyboardInterrupt:
            print("\n收到停止信號")
        except Exception as e:
            print(f"程式執行錯誤: {e}")
        finally:
            self.shutdown()
    
    def main_loop(self):
        """主監控迴圈"""
        status_interval = 30  # 每30秒顯示一次狀態
        
        while True:
            time.sleep(status_interval)
            self.show_status()
    
    def show_status(self):
        """顯示當前狀態"""
        status = self.thread_manager.get_thread_status()
        
        print("\n=== 系統狀態 ===")
        print(f"執行緒管理器運行: {status['running']}")
        
        # 顯示執行緒狀態
        for name, thread_info in status['threads'].items():
            status_text = "運行中" if thread_info['alive'] else "已停止"
            print(f"{name}執行緒: {status_text}")
        
        # 顯示最新資料
        vars_info = status['runtime_vars']
        print(f"Ping延遲: {vars_info['ping_latency']}ms")
        print(f"封包遺失: {vars_info['ping_packet_loss']}%")
        print(f"下載速度: {vars_info['network_rx_speed']}KB/s")
        print(f"上傳速度: {vars_info['network_tx_speed']}KB/s")
        print(f"最後報告: {vars_info['last_report_status']} at {vars_info['last_report_time']}")
        print("=" * 20)
    
    def shutdown(self):
        """關閉應用程式"""
        print("正在關閉監控系統...")
        self.thread_manager.stop_all_threads()
        print("監控系統已關閉")


def main():
    """主程式入口"""
    app = NetworkMonitorApp()
    app.start()


if __name__ == "__main__":
    main()
