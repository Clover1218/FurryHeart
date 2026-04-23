import asyncio
import websockets
import json

async def test_ws_connection():
    """测试 WebSocket 连接"""
    device_id = "test"
    ws_url = f"ws://localhost:8000/api/ws/{device_id}"
    
    print(f"正在连接到 WebSocket 服务器: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"WebSocket 连接成功！设备 ID: {device_id}")
            print("等待接收消息...")
            
            # 发送一个测试消息
            test_message = {
                "type": "ping",
                "timestamp": "2026-04-09T12:00:00"
            }
            await websocket.send(json.dumps(test_message))
            print(f"已发送测试消息: {test_message}")
            
            # 持续接收消息
            while True:
                try:
                    message = await websocket.recv()
                    print(f"接收到消息: {message}")
                    
                    # 解析消息
                    try:
                        data = json.loads(message)
                        print(f"解析后的消息: {data}")
                    except json.JSONDecodeError:
                        print("消息不是有效的 JSON")
                        
                except websockets.ConnectionClosed:
                    print("WebSocket 连接已关闭")
                    break
                except Exception as e:
                    print(f"接收消息时出错: {e}")
                    break
                    
    except Exception as e:
        print(f"连接失败: {e}")
        print("请确保服务端正在运行，并且设备 ID 'test' 已在设备表中注册")

if __name__ == "__main__":
    asyncio.run(test_ws_connection())
