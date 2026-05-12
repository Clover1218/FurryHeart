
"""FastAPI 热重载启动脚本"""

import os
import sys
import uvicorn

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # 获取环境变量配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"Starting FastAPI server on {host}:{port}")
    print(f"Hot reload: {'Enabled' if reload else 'Disabled'}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["."],  # 监控当前目录下的所有文件
        reload_includes=["*.py"],  # 只监控 Python 文件
        log_level="info"
    )

if __name__ == "__main__":
    main()
