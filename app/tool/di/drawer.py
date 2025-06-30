import json
from typing import Any, Hashable, Dict, Literal

from pydantic import BaseModel

from app.tool.chart_visualization.data_visualization import DataVisualization
from app.logger import logger

"""
https://github.com/pyecharts/pyecharts
https://github.com/pyecharts/snapshot-selenium
https://medium.com/firebird-technologies/building-an-agent-for-data-visualization-plotly-39310034c4e9
https://github.com/microsoft/lida?tab=readme-ov-file
"""

_DI_DRAWER_TOOL_DESCRIPTION = """
这是一个画图工具，使用开源工具vmind，根据用户输入json/csv格式数据画出对应类型图表，并给出一些基础洞察分析
1.图表输出格式可以为 (png)
2.基础洞察分析输出格式为 (.md)
"""


class Drawer(DataVisualization):
    name: str = "drawer"
    description: str = _DI_DRAWER_TOOL_DESCRIPTION

    async def execute(self,
                      json_path: str,
                      output_type: str | None = "png",
                      tool_type: Literal["visualization"] = "visualization",
                      language: str | None = "zh") -> Dict:
        if tool_type != "visualization":
            return {
                "observation": f"Only support 'visualization' tool_type now",
                "success": False,
            }
        try:
            logger.info(f"📈 di drawer with {json_path} in: {tool_type} ")
            with open(json_path, "r", encoding="utf-8") as file:
                json_info = json.load(file)
            return await self.data_visualization(json_info['config'], output_type, language)
        except Exception as e:
            return {
                "observation": f"Error: {e}",
                "success": False,
            }

    async def invoke_vmind(self,
                           file_name: str,
                           output_type: str,
                           task_type: str,
                           insights_id: list[str] = None,
                           dict_data: list[dict[Hashable, Any]] = None,
                           chart_description: str = None,
                           language: str = "en",
                           ts_path: str = "src/chartVisualize.ts") -> Dict:
        # todo add chart preference
        return await super().invoke_vmind(file_name,
                                          'png',
                                          task_type,
                                          insights_id,
                                          dict_data,
                                          chart_description,
                                          'zh',
                                          "src/chartVisualize.ts")


class ChartApi(BaseModel):
    type: Literal["line", "area", "pie", "bar"] = "area"
    width: int
    height: int
