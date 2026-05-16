#!/usr/bin/env python3
"""
WebSocket 测试脚本

用于测试 /ws/{device_id} 接口的连接功能
"""

import asyncio
import websockets
import argparse
import sys
import json


async def connect_to_server(server_host: str, server_port: int, device_id: str):
    """
    连接到 WebSocket 服务器
    
    Args:
        server_host: 服务器地址
        server_port: 服务器端口
        device_id: 设备ID
    """
    # 构建 WebSocket URL
    ws_url = f"ws://{server_host}:{server_port}/api/ws/{device_id}"
    
    print(f"[INFO] 尝试连接到: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"[SUCCESS] 设备 {device_id} 连接成功！")
            print("[INFO] 已建立 WebSocket 连接，等待消息...")
            print("[INFO] 按 Ctrl+C 断开连接")
            
            # 持续监听消息
            async for message in websocket:
                print(f"[RECEIVED] {message}")
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[ERROR] 连接失败，服务器返回错误状态码: {e}")
        if e.status_code == 1008:
            print("[ERROR] 设备不存在，请检查 device_id 是否正确")
    except ConnectionRefusedError:
        print(f"[ERROR] 无法连接到服务器 {server_host}:{server_port}")
        print("[ERROR] 请检查服务器是否正在运行，或地址/端口是否正确")
    except KeyboardInterrupt:
        print(f"\n[INFO] 用户中断，设备 {device_id} 断开连接")
    except Exception as e:
        print(f"[ERROR] 发生未知错误: {e}")


def main():
    """
    主函数
    """

    host="localhost"
    port="8000"
    device_id="123456"
    # 打印配置信息
    print("=" * 50)
    print("WebSocket 测试脚本配置")
    print("=" * 50)
    print(f"  服务器地址: {host}")
    print(f"  服务器端口: {port}")
    print(f"  设备ID: {device_id}")
    print("=" * 50)
    
    # 运行连接测试
    try:
        asyncio.run(connect_to_server(host, port, device_id))
    except KeyboardInterrupt:
        print("\n[INFO] 程序退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
