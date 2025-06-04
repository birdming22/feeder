# test_udp_receiver.py - 快速測試用
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 8080))
print("UDP接收端已啟動，等待資料...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"收到來自 {addr} 的資料:")
    print(json.dumps(json.loads(data.decode('utf-8')), indent=2))
    print("-" * 50)
