from typing import Dict, Any, List
from repositories.config_repo import ConfigRepo


class ConfigService:
    def __init__(self, config_repo: ConfigRepo):
        self.config_repo = config_repo

    async def get_user_final_config(self, user_id: str) -> Dict[str, Any]:
        """获取用户最终配置（合并默认/系统/用户）"""
        # 获取所有 schema
        schemas = await self.config_repo.get_all_schema()
        # 获取系统配置
        system_configs = await self.config_repo.get_all_system_configs()
        # 获取用户配置
        user_configs = await self.config_repo.get_all_user_configs(user_id)

        # 构建默认配置
        default_config = {schema['key']: schema['default_value'] for schema in schemas}
        # 合并系统配置
        merged_config = {**default_config, **system_configs}
        # 合并用户配置
        merged_config.update(user_configs)

        return merged_config

    async def get_ui_config(self, user_id: str) -> Dict[str, Any]:
        """获取前端渲染需要的分组数据"""
        # 获取所有 schema
        schemas = await self.config_repo.get_all_schema()
        # 获取最终配置
        final_config = await self.get_user_final_config(user_id)

        # 按分组组织配置
        ui_config = {}
        for schema in schemas:
            key = schema['key']
            # 提取分组信息（假设 key 格式为 group.key）
            parts = key.split('.')
            if len(parts) >= 2:
                group = parts[0]
                config_key = '.'.join(parts[1:])
            else:
                group = 'default'
                config_key = key

            if group not in ui_config:
                ui_config[group] = []

            ui_config[group].append({
                'key': key,
                'config_key': config_key,
                'type': schema['type'],
                'options': schema['options'],
                'description': schema['description'],
                'current_value': final_config.get(key, schema['default_value'])
            })

        return ui_config

    async def update_user_config(self, user_id: str, updates: Dict[str, Any]):
        """校验并批量更新用户配置"""
        # 获取所有 schema
        schemas = await self.config_repo.get_all_schema()
        schema_map = {schema['key']: schema for schema in schemas}

        # 校验配置
        validated_updates = {}
        for key, value in updates.items():
            if key not in schema_map:
                continue  # 忽略不存在的配置项

            schema = schema_map[key]
            if await self._validate_config(value, schema):
                validated_updates[key] = value

        # 批量写入
        if validated_updates:
            await self.config_repo.batch_upsert_user_config(user_id, validated_updates)

    async def _validate_config(self, value: Any, schema: Dict[str, Any]) -> bool:
        """验证配置值是否符合 schema"""
        print(schema)
        config_type = schema.get('type')
        options = schema.get('options', {})
        print(config_type)
        # 类型验证
        if config_type == 'string' and not isinstance(value, str):
            return False
        elif config_type == 'number' and not isinstance(value, (int, float)):
            return False
        elif config_type == 'boolean' and not isinstance(value, bool):
            return False
        elif config_type == 'enum':
            enum_options = options.get('enum', [])
            if value not in enum_options:
                return False
        elif config_type == 'object' and not isinstance(value, dict):
            return False

        # 其他验证规则
        # if config_type == 'string':
        #     min_length = options.get('min_length')
        #     max_length = options.get('max_length')
        #     if min_length is not None and len(value) < min_length:
        #         return False
        #     if max_length is not None and len(value) > max_length:
        #         return False
        # elif config_type == 'number':
        #     minimum = options.get('minimum')
        #     maximum = options.get('maximum')
        #     if minimum is not None and value < minimum:
        #         return False
        #     if maximum is not None and value > maximum:
        #         return False

        return True
