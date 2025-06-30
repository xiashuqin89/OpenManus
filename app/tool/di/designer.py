from typing import Any

from app.tool.base import BaseTool, ToolResult


_DI_DESIGNER_TOOL_DESCRIPTION = """
这是一个数据处理流程设计工具，主要负责规划和创建数据处理任务，将复杂任务拆分成一个一个步骤.
该工具提供任务创建、步骤更新、任务追溯等函数.
"""


class DiDesignerTool(BaseTool):
    """
    这是一个数据处理流程设计工具，主要负责规划和创建数据处理任务，将复杂任务拆分成一个一个步骤.
    该工具提供任务创建、步骤更新、任务追溯等函数.
    """

    name: str = "designer"
    description: str = _DI_DESIGNER_TOOL_DESCRIPTION
    parameters: dict = {}

    async def execute(self, **kwargs) -> Any:
        pass
