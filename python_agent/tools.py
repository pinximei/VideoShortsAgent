"""
Tool 注册系统

将 Python 函数注册为 LLM 可调用的"工具"（Tool）。
这是 Agent 的核心基础设施 —— 让 LLM 知道自己有哪些能力可以使用。

核心概念：
- Tool：一个函数 + 它的描述信息（名称、参数、用途）
- Function Calling：LLM 返回的不是文字，而是"我要调用某个函数"的指令
- Tool Schema：告诉 LLM 工具长什么样的 JSON 描述

使用示例：
    registry = ToolRegistry()

    @registry.register("转录视频", {"video_path": "视频文件路径"})
    def transcribe(video_path: str) -> str:
        ...

    # 获取所有工具的 schema（传给 LLM）
    schemas = registry.get_schemas()

    # 根据 LLM 返回的工具名执行
    result = registry.call("transcribe", {"video_path": "a.mp4"})
"""
import json
from typing import Callable, Any


class Tool:
    """单个工具的封装

    Attributes:
        name: 工具名称（英文，LLM 通过它来调用）
        description: 工具描述（告诉 LLM 这个工具做什么）
        parameters: 参数描述 {参数名: 说明}
        func: 实际执行的 Python 函数
    """

    def __init__(self, name: str, description: str, parameters: dict, func: Callable = None):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_schema(self) -> dict:
        """转换为 OpenAI Function Calling 格式的 schema

        这个格式是 LLM API 的标准，告诉模型：
        - 工具叫什么名字
        - 工具做什么
        - 需要哪些参数、每个参数是什么类型
        """
        properties = {}
        required = []
        for param_name, param_desc in self.parameters.items():
            properties[param_name] = {
                "type": "string",
                "description": param_desc
            }
            required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def call(self, **kwargs) -> Any:
        """执行工具"""
        return self.func(**kwargs)


class ToolRegistry:
    """工具注册表

    管理所有可用工具，提供注册、查询、调用功能。
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def add(self, name: str, description: str, parameters: dict, func: Callable):
        """注册一个工具

        Args:
            name: 工具名称
            description: 工具功能描述
            parameters: 参数描述 {参数名: 说明}
            func: 实际执行的函数
        """
        self._tools[name] = Tool(name, description, parameters, func)

    def get_schemas(self) -> list[dict]:
        """获取所有工具的 schema 列表（传给 LLM）"""
        return [tool.to_schema() for tool in self._tools.values()]

    def call(self, name: str, arguments: dict) -> str:
        """根据名称调用工具

        Args:
            name: 工具名称
            arguments: 参数字典

        Returns:
            工具执行结果的字符串表示（反馈给 LLM）
        """
        if name not in self._tools:
            return f"错误：未知工具 '{name}'，可用工具：{list(self._tools.keys())}"

        try:
            result = self._tools[name].call(**arguments)
            # 将结果转为字符串（LLM 只能接收文本）
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result)
        except Exception as e:
            return f"工具执行出错：{e}"

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名"""
        return list(self._tools.keys())
