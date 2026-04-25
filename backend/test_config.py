import asyncio
from core.db import create_pool
from repositories.config_repo import ConfigRepo
from services.config_service import ConfigService


async def test_config():
    # 创建数据库连接池
    pool = await create_pool()
    
    try:
        # 初始化 ConfigRepo
        config_repo = ConfigRepo(pool)
        # 初始化 ConfigService
        config_service = ConfigService(config_repo)
        
        # 测试获取所有配置 schema
        print("获取所有配置 schema:")
        schemas = await config_repo.get_all_schema()
        for schema in schemas:
            print(f"  - {schema['key']}: {schema['type']}")
        
        # 测试获取系统配置
        print("\n获取系统配置:")
        system_configs = await config_repo.get_all_system_configs()
        print(system_configs)
        
        # 测试获取用户配置
        test_user_id = "user_123"
        print(f"\n获取用户 {test_user_id} 的配置:")
        user_configs = await config_repo.get_all_user_configs(test_user_id)
        print(user_configs)
        
        # 测试更新用户配置
        print("\n更新用户配置:")
        updates = {
            "chat.max_history": 50,
            "chat.temperature": 0.7,
            "ui.theme": "dark"
        }
        await config_service.update_user_config(test_user_id, updates)
        print("配置更新成功")
        
        # 测试获取用户最终配置
        print(f"\n获取用户 {test_user_id} 的最终配置:")
        final_config = await config_service.get_user_final_config(test_user_id)
        print(final_config)
        
        # 测试获取 UI 配置
        print(f"\n获取用户 {test_user_id} 的 UI 配置:")
        ui_config = await config_service.get_ui_config(test_user_id)
        for group, configs in ui_config.items():
            print(f"  {group}:")
            for config in configs:
                print(f"    - {config['config_key']}: {config['current_value']} ({config['type']})")
                
    finally:
        # 关闭连接池
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_config())
