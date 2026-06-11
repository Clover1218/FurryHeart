# state.py

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import AsyncIterator
import logging

from pydantic import BaseModel, Field
from services.config_service import ConfigService
from services.emotion_service import EmotionService
from services.session_service import SessionService
from services.history_service import HistoryService
from services.memory_service import MemoryService
from services.llm_service import LLMService
from services.scene_service import SceneService
from core.prompt import base_chat_template,system_base_prompt,system_base_prompt_p2,entity_extract_template,scene_info_complex_prompt,scene_info_medium_prompt


from typing import Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolRuntime, ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage,ToolMessage,HumanMessage,AIMessage

@dataclass
class Context:
    user_id: str
    device_id: str

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class SearchHistoryInput(BaseModel):
    start_time: datetime = Field(description="查询的开始时间，ISO格式，例如 '2025-06-01T00:00:00'")
    end_time: datetime = Field(description="查询的结束时间，ISO格式")
    
class ChatAgent:

    def __init__(self,
                 session_svc:SessionService,
                 emotion_svc:EmotionService,
                 history_svc:HistoryService,
                 memory_svc:MemoryService,
                 scene_svc: SceneService,
                 llm_svc:LLMService,
                 config_svc:ConfigService,
                 model:ChatDeepSeek,
                 logger:logging.Logger):

        self.session_svc = session_svc
        self.scene_svc = scene_svc
        self.emotion_svc = emotion_svc
        self.history_svc = history_svc
        self.memory_svc = memory_svc
        self.llm_svc = llm_svc
        self.config_svc = config_svc
        self.logger=logger
        self.tools = self._bulid_tools()
        self.model = model.bind_tools(self.tools)
        self.graph = self._build_graph()
    def _bulid_tools(self):
        
        @tool
        async def search_memory_by_keywords(
            keywords:List[str],
            runtime: ToolRuntime[Context],
            ) ->str:
            """记忆查找工具，传入关键词，可以使用embedding模型从数据库中查询最相似的5条记忆"""
           
            memories=await self.memory_svc.query_memory(runtime.context.user_id,runtime.context.device_id,keywords,5)
            memories_string:str='\n'.join(event['content'] for event in memories)
            print(memories_string)
            return memories_string
        @tool(args_schema=SearchHistoryInput)
        async def get_recent_history(
            start_time: datetime,
            end_time: datetime,
            runtime: ToolRuntime[Context],
        ) -> str:
            """可以查询指定时间范围内你与用户的聊天记录"""
            self.logger.info(f"查询{start_time}~{end_time}之间的历史")
            content, artifact = await self.history_svc.query_history_by_time(runtime.context.user_id, 
                                                                runtime.context.device_id, 
                                                                start_time, end_time)
            self.logger.info(f"结果是{artifact}")
            return artifact
        # @tool
        # def get_scene_response_strategy(scene_id:int):
        #     pass
        @tool 
        def get_clover() -> str:
            """调用该记录可以获得Clover(一个人名)的信息"""
            print("调用get_clover")
            return "此人是一个除了打游戏一无是处的人"

        return [get_recent_history,search_memory_by_keywords]




    def _build_graph(self):
        graph = StateGraph(AgentState,context_schema=Context)
        graph.add_node("llm",self._call_model)
        graph.add_node("tools",ToolNode(self.tools))
        graph.add_edge(START,"llm")
        graph.add_conditional_edges(
            "llm",self._should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        graph.add_edge("tools","llm")
        return graph.compile()


    async def _call_model(self, state: AgentState):
        today = datetime.now().strftime("%Y年%m月%d日")
        system_prompt = SystemMessage(content=f"当前日期是 {today}。\n{system_base_prompt}\n{scene_info_medium_prompt}\n{system_base_prompt_p2}")
        response = await self.model.ainvoke([system_prompt] + state["messages"])
        return {"messages": [response]}

    def _should_continue(self, state: AgentState):
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END


    async def chat(self,user_input: str, user_id: str, device_id: str) -> str:
        session = await self.session_svc.get_session(user_id,user_id)
        session_id=session["session_id"]
        history_items=await self.history_svc.get_previous_history(user_id,device_id)
        history_messages = []
        for item in history_items:
            # 格式化时间：例如 "2025-06-11 14:30"
            time_str = item.created_at.strftime("%Y-%m-%d %H:%M")
            if item.role == "user":
                content = f"{time_str} 用户：{item.content}"
                history_messages.append(HumanMessage(content=content))
            else:  # assistant
                content = f"{time_str} 绒绒：{item.content}"
                history_messages.append(AIMessage(content=content))

        all_messages = history_messages + [HumanMessage(content=user_input)]
        await self.history_svc.add_history(user_id, session_id,"user", user_input)
        result = await self.graph.ainvoke(
            {"messages": all_messages},
            context=Context(user_id=user_id, device_id=device_id)
        )
        reply=result["messages"][-1].content
        await self.session_svc.update(user_id)
        await self.history_svc.add_history(user_id, session_id,"assistant", reply)
        return reply

    async def chat_stream(self, device_id, user_input) -> AsyncIterator[str]:
        prompt="做个自我介绍"
        full_reply = ""
        async for chunk in self.llm_svc.generate_stream(prompt):
            full_reply += chunk
            yield chunk
        



