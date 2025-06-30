import os
import time
from typing import Dict

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.tool import Terminate, ToolCollection
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.di.gather_data import DIGatherData
from app.tool.di.drawer import Drawer
from app.tool.di.report import DIReport
from app.config import config
from app.logger import logger
from app.prompt.di import SYSTEM_PROMPT, NEXT_STEP_PROMPT


class DI(ToolCallAgent):
    """Data Interpreter"""

    name: str = "DI"
    description: str = "一个数据处理分析AI Agent, 能够使用各种工具(包含mcp工具)解决实现不同的任务"

    system_prompt: str = SYSTEM_PROMPT.format(directory=os.path.join(config.workspace_root, 'di'),
                                              now=time.time())
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 10
    # MCP clients for remote tool access
    mcp_clients: MCPClients = None

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            DIGatherData(),
            Drawer(),
            DIReport(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(
        default_factory=dict
    )  # server_id -> url/command
    _initialized: bool = False

    @classmethod
    def create(cls, **kwargs) -> "DI":
        """Factory method to create and properly initialize a DI instance."""
        instance = cls(**kwargs)
        # add other tool
        instance._initialized = True
        return instance

    async def cleanup(self):
        """Clean up DI agent resources."""
        if self._initialized:
            self._initialized = False

    async def think(self) -> bool:
        logger.info(self.next_step_prompt)
        logger.info(self.memory.messages)
        result = await super().think()
        return result
