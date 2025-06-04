#!/usr/bin/env python3
"""
網路效能監控程式 - 2天開發版本
功能：監控網卡延遲、封包遺失、吞吐量，並透過UDP傳送資料
"""

import json
import time
import socket
import psutil
import subprocess
import threading
from datetime import datetime
from typing import Dict, Any, Optional

class NetworkMonitor:
    def __init__(self, config_file: str = "config.json"):
        """初始化網路監控器"""
        self.config = self.load_config(config_file)
        self.running = False
        self.last_net_stats = None
        
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """載入配置檔案"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.validate_config(config)
            return config
        except FileNotFoundError:
            print(f"配置檔案 {config_file} 不存在，使用預設配置")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"配置檔案格式錯誤: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置"""
        return {
            "interface": "eth0",
            "target_ip": "8.8.8.8", 
            "udp_server": {
                "ip": "127.0.0.1",
                "port": 8080
            },
            "interval": 30,
            "ping_count": 5
        }
    
    def validate_config(self, config: Dict[str, Any]):
        """驗證配置有效性"""
        required_keys = ["interface", "target_ip", "udp_server"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置缺少必要項目: {key}")
    
    def get_available_interfaces(self) -> list:
        """獲取可用網路介面"""
        interfaces = []
        net_if_stats = psutil.net_if_stats()
        for interface, stats in net_if_stats.items():
            if stats.isup:
                interfaces.append(interface)
        return interfaces
    
    def get_latency_and_packet_loss(self, target_ip: str, count: int = 5) -> Dict[str, float]:
        """測量延遲和封包遺失率"""
        try:
            # 使用系統ping指令
            if hasattr(subprocess, 'DEVNULL'):
                devnull = subprocess.DEVNULL
            else:
                devnull = open('nul' if os.name == 'nt' else '/dev/null', 'w')
            
            # 構建ping指令
            ping_cmd = ["ping", "-c", str(count), target_ip]
            if os.name == 'nt':  # Windows
                ping_cmd = ["ping", "-n", str(count), target_ip]
            
            result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return self.parse_ping_output(result.stdout, os.name == 'nt')
            else:
                print(f"Ping失敗: {result.stderr}")
                return {"latency": -1, "packet_loss": 100}
                
        except Exception as e:
            print(f"延遲測試錯誤: {e}")
            return {"latency": -1, "packet_loss": 100}
    
    def parse_ping_output(self, output: str, is_windows: bool) -> Dict[str, float]:
        """解析ping輸出結果"""
        latency = -1
        packet_loss = 100
        
        try:
            lines = output.split('\n')
            
            if is_windows:
                # Windows ping輸出解析
                for line in lines:
                    if "Average" in line:
                        latency = float(line.split('=')[-1].replace('ms', '').strip())
                    elif "Lost" in line:
                        # 解析遺失率
                        lost_part = line.split('(')[1].split('%')[0]
                        packet_loss = float(lost_part)
            else:
                # Linux/macOS ping輸出解析
                for line in lines:
                    if "avg" in line or "平均" in line:
                        parts = line.split('/')
                        if len(parts) >= 4:
                            latency = float(parts[-2])
                    elif "packet loss" in line or "封包遺失" in line:
                        packet_loss = float(line.split('%')[0].split()[-1])
        except Exception as e:
            print(f"解析ping結果錯誤: {e}")
        
        return {"latency": latency, "packet_loss": packet_loss}
    
    def get_throughput(self, interface: str) -> Dict[str, float]:
        """獲取網卡吞吐量"""
        try:
            # 獲取網卡統計資訊
            net_io_counters = psutil.net_io_counters(pernic=True)
            
            if interface not in net_io_counters:
                print(f"找不到網卡: {interface}")
                available = list(net_io_counters.keys())
                print(f"可用網卡: {available}")
                if available:
                    interface = available[0]
                    print(f"使用網卡: {interface}")
                else:
                    return {"rx_speed": 0, "tx_speed": 0}
            
            current_stats = net_io_counters[interface]
            current_time = time.time()
            
            if self.last_net_stats is None:
                self.last_net_stats = (current_stats, current_time)
                time.sleep(1)  # 等待1秒進行第二次測量
                return self.get_throughput(interface)
            
            last_stats, last_time = self.last_net_stats
            time_diff = current_time - last_time
            
            if time_diff > 0:
                rx_speed = (current_stats.bytes_recv - last_stats.bytes_recv) / time_diff
                tx_speed = (current_stats.bytes_sent - last_stats.bytes_sent) / time_diff
                
                # 更新統計資訊
                self.last_net_stats = (current_stats, current_time)
                
                return {
                    "rx_speed": round(rx_speed / 1024, 2),  # KB/s
                    "tx_speed": round(tx_speed / 1024, 2)   # KB/s
                }
            else:
                return {"rx_speed": 0, "tx_speed": 0}
                
        except Exception as e:
            print(f"吞吐量測試錯誤: {e}")
            return {"rx_speed": 0, "tx_speed": 0}
    
    def collect_performance_data(self) -> Dict[str, Any]:
        """收集所有效能資料"""
        print("開始收集效能資料...")
        
        # 獲取延遲和封包遺失
        latency_data = self.get_latency_and_packet_loss(
            self.config["target_ip"], 
            self.config.get("ping_count", 5)
        )
        
        # 獲取吞吐量
        throughput_data = self.get_throughput(self.config["interface"])
        
        # 組合所有資料
        performance_data = {
            "timestamp": datetime.now().isoformat(),
            "interface": self.config["interface"],
            "target_ip": self.config["target_ip"],
            "latency_ms": latency_data["latency"],
            "packet_loss_percent": latency_data["packet_loss"],
            "rx_speed_kbps": throughput_data["rx_speed"],
            "tx_speed_kbps": throughput_data["tx_speed"]
        }
        
        print(f"收集完成: 延遲={latency_data['latency']}ms, "
              f"遺失率={latency_data['packet_loss']}%, "
              f"下載={throughput_data['rx_speed']}KB/s, "
              f"上傳={throughput_data['tx_speed']}KB/s")
        
        return performance_data
    
    def send_udp_data(self, data: Dict[str, Any]) -> bool:
        """透過UDP傳送資料"""
        try:
            # 建立UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)  # 5秒超時
            
            # 將資料轉換為JSON字串
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            # 傳送資料
            server_ip = self.config["udp_server"]["ip"]
            server_port = self.config["udp_server"]["port"]
            
            sock.sendto(json_data.encode('utf-8'), (server_ip, server_port))
            sock.close()
            
            print(f"資料已傳送至 {server_ip}:{server_port}")
            return True
            
        except Exception as e:
            print(f"UDP傳送失敗: {e}")
            return False
    
    def run_once(self):
        """執行一次完整的監控循環"""
        try:
            # 收集效能資料
            performance_data = self.collect_performance_data()
            
            # 傳送資料
            success = self.send_udp_data(performance_data)
            
            if success:
                print("監控循環完成")
            else:
                print("資料傳送失敗")
                
        except Exception as e:
            print(f"監控循環錯誤: {e}")
    
    def run(self):
        """開始持續監控"""
        self.running = True
        interval = self.config.get("interval", 30)
        
        print(f"開始監控網卡: {self.config['interface']}")
        print(f"目標IP: {self.config['target_ip']}")
        print(f"UDP伺服器: {self.config['udp_server']['ip']}:{self.config['udp_server']['port']}")
        print(f"監控間隔: {interval}秒")
        print("按Ctrl+C停止監控")
        
        try:
            while self.running:
                self.run_once()
                
                # 等待指定間隔
                for i in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n收到停止信號")
        except Exception as e:
            print(f"監控執行錯誤: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止監控"""
        self.running = False
        print("監控已停止")

def create_sample_config():
    """創建範例配置檔案"""
    sample_config = {
        "interface": "eth0",
        "target_ip": "8.8.8.8",
        "udp_server": {
            "ip": "127.0.0.1",
            "port": 8080
        },
        "interval": 30,
        "ping_count": 5
    }
    
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print("已創建範例配置檔案: config.json")

def main():
    """主程式入口"""
    import sys
    import os
    
    # 檢查是否存在配置檔案
    if not os.path.exists("config.json"):
        print("未找到配置檔案，創建範例配置...")
        create_sample_config()
        print("請編輯 config.json 設定您的監控參數，然後重新執行程式")
        return
    
    # 創建監控器並開始執行
    monitor = NetworkMonitor()
    
    # 顯示可用網卡
    available_interfaces = monitor.get_available_interfaces()
    print(f"可用網卡: {available_interfaces}")
    
    # 開始監控
    monitor.run()

if __name__ == "__main__":
    main()
