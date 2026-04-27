from core.prompt import scene_detect_template
from services.llm_service import LLMService
from typing import List, Dict, Any

class SceneService:

    def __init__(self, llm_service, logger):
        self.llm: LLMService = llm_service
        self.logger = logger

    async def detect(self, text: str):
        reply_json = await self.llm.generate(scene_detect_template.render(input=text))
        return reply_json

    async def get_scene(self, scenes: List[Dict[str, str]], history: str) -> Dict[str, str]:
        """
        根据场景列表和历史记录判断当前场景并返回对应的回复策略
        
        Args:
            scenes: 场景列表，每个场景包含 scene_name, condition, response_text
            history: 历史记录字符串
            
        Returns:
            包含 scene_name 和 response_text 的字典
        """
        try:
            # 提取所有场景名称和判断条件
            scene_conditions = []
            scene_map = {}
            
            for scene in scenes:
                scene_name = scene.get('scene_name', '')
                condition = scene.get('condition', '')
                response_text = scene.get('response_text', '')
                
                if scene_name and condition:
                    scene_conditions.append(f"场景 '{scene_name}' 的判断条件: {condition}")
                    scene_map[scene_name] = response_text
            
            # 拼接场景条件和历史记录 scene_detect_template
            prompt = """
            # 你是一个场景判断助手，你需要根据用户与绒绒的对话记录，来判断用户处于哪一个场景
            
            ## 可用场景及其判断条件:
            {scene_conditions}
            
            ## 历史记录:
            {history}
            
            ## 任务:
            请根据历史记录(已经按照时间升序排序，即越后面的是最新的)，判断用户当前处于哪个场景。
            只需要返回场景名称，不要返回其他内容。
            如果没有匹配的场景，或者没有足够的证据进行准确推断，请返回 "无"
            """
            
            scene_conditions_str = "\n".join(scene_conditions)
            prompt = prompt.format(
                scene_conditions=scene_conditions_str,
                history=history
            )
            
            # 调用 LLM 获取判断的场景
            detected_scene = await self.llm.generate(prompt)
            detected_scene = detected_scene.strip()
            
            # 根据场景返回对应的回复策略
            if detected_scene in scene_map:
                return {
                    "scene_name": detected_scene,
                    "response_strategy": scene_map[detected_scene]
                }
            else:
                return {
                    "scene_name": "无",
                    "response_strategy": ""
                }
                
        except Exception as e:
            self.logger.error(f"场景判断失败: {e}")
            return {
                "scene_name": "无",
                "response_strategy": ""
            }
