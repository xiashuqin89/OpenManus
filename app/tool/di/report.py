import json
from typing import List, Dict, Literal, Union

from pydantic import Field, BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader, Template

from app.tool.base import BaseTool, ToolResult
from app.tool.di.drawer import Drawer
from app.api import BKService
from app.llm import LLM
from app.schema import Message
from app.config import config


_DI_ANALYST_TOOL_DESCRIPTION = """
这是一个数据分析报告制作工具，依赖drawer工具输出，根据输入的json/csv离线数据，或者api动态数据，按照以下要求给出专业且多维度分析报告
1. **结构清晰**：包含摘要、分析、结论、建议四部分  
2. **受众适配**：  
   - 技术团队版：侧重方法论与数据细节  
   - 管理层版：用ROI、趋势图表、关键决策点  
3. **必含模块**：  
   - 数据质量说明（完整性/准确性评分）  
   - 核心指标变化（环比/同比/达成率）  
   - 根因分析（至少3个假设验证）  
   - 风险预警（3σ异常检测+业务解释）
4. **技术栈**：
   - 可视化：[Tableau/Power BI代码片段/截图规范]
5. **输出**：
   - 输出一份markdown格式的分析报告
   - 如果有`图片`格式输入请正确渲染出来
"""


class SingleMetricDesc(BaseModel):
    metric_field_name: str
    datapoints: Union[List, str]
    chart_path: str = ""
    single_insight: str

    def __str__(self):
        return f'{self.metric_field_name}' \
               f'- 原始数据: {self.datapoints}' \
               f'- 指标图: {self.chart_path}' \
               f'- 基本描述: {self.single_insight}'


class UserPrompt(BaseModel):
    metrics_desc: List[SingleMetricDesc]

    def __str__(self):
        metrics_desc = "\n".join([str(item) for item in self.metrics_desc])
        return f'请综合以下指标给出数据分析报告:' \
               f'{metrics_desc}'


class DIReport(BaseTool):
    """
    这是一个数据分析报告制作工具，，依赖drawer工具输出，根据输入的json/csv离线数据，或者api动态数据，按照以下要求给出专业且多维度分析报告
    1. **结构清晰**：包含摘要、分析、结论、建议四部分
    2. **受众适配**：
       - 技术团队版：侧重方法论与数据细节
       - 管理层版：用ROI、趋势图表、关键决策点
    3. **必含模块**：
       - 数据质量说明（完整性/准确性评分）
       - 核心指标变化（环比/同比/达成率）
       - 根因分析（至少3个假设验证）
       - 风险预警（3σ异常检测+业务解释）
    4. **技术栈**：
       - 可视化：[Tableau/Power BI代码片段/截图规范]
    5. **输出**：
       - 输出一份markdown格式的分析报告
    """

    name: str = "report"
    description: str = _DI_ANALYST_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "json_config_path": {
                "type": "string",
                "description": """file path of json info with ".json" in the end, it's output of the gather_data""",
            },
            "language": {
                "description": "english(en) / chinese(zh)",
                "type": "string",
                "default": "en",
                "enum": ["zh", "en"],
            },
        },
        "required": ["json_config_path"],
    }
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    bk_service: BKService = None

    async def execute(self, json_config_path: str, **kwargs) -> ToolResult:
        with open(json_config_path, "r", encoding="utf-8") as file:
            json_config = json.load(file)

        user_prompt = []
        for item in json_config['config']:
            try:
                with open(item['csvFilePath'], "r", encoding="utf-8") as f:
                    datapoints = f.read()
            except FileNotFoundError:
                return ToolResult(error="Report error: can not find data file")

            try:
                with open(item['insightsFilePath'], "r", encoding="utf-8") as f:
                    single_insight = f.read()
            except FileNotFoundError:
                single_insight = ''
                await Drawer().execute(json_config_path)

            single_metric_desc = SingleMetricDesc(metric_field_name=item["name"],
                                                  single_insight=single_insight,
                                                  chart_path=item.get("chartFilePath", ""),
                                                  datapoints=datapoints)
            user_prompt.append(single_metric_desc)

        system_message = Message.system_message(_DI_ANALYST_TOOL_DESCRIPTION)
        user_message = Message.user_message(str(UserPrompt(metrics_desc=user_prompt)))
        response = await self.llm.ask(
            messages=[user_message], system_msgs=[system_message], stream=False
        )
        content = self._trim(response)
        content = await self._render(json_config, content)
        self._save(json_config_path, content, 'html')
        return ToolResult(output=response)

    async def _analyze(self, json_config: Dict) -> Dict:
        """
        1. biz basic info
        """
        if config.bk_config is None:
            return None

        bk_config = config.bk_config
        self.bk_service = BKService(bk_config.product,
                                    bk_config.api_root,
                                    bk_config.bk_app_code,
                                    bk_config.bk_app_secret)
        response = await self.bk_service.bkcmdb.search_business(condition={
            "bk_biz_id": int(json_config["bk_biz_id"])
        })
        if response["count"] == 0:
            return None
        return response["info"][0]

    @staticmethod
    def _trim(content: str) -> str:
        return content.lstrip('markdown```').rstrip('```').replace('```', '').replace('`', '')

    async def _render(self, json_config: Dict, content: str, template_name: Literal['dark'] = 'dark') -> str:
        """
        1. main view
        2. convert md to html or poster
        """
        env = Environment(loader=FileSystemLoader(f"{config.workspace_root}/../app/tool/di/templates"))
        template = env.get_template(f'{template_name}.html')
        stats, charts = [], []
        for item in json_config['config']:
            with open(item['insights'], "r", encoding="utf-8") as file:
                insights = json.load(file)
            for metric in insights['insights']:
                stats.append({
                    'name': f"{item['name']} {metric['type']}",
                    'value': metric['value'],
                })
                charts.append({
                    "src": f"https://placehold.co/400x200?text={metric['value']}"
                })
        basic_info = await self._analyze(json_config)
        result = template.render(report=content,
                                 stats=stats,
                                 # charts=charts,
                                 banner_text=basic_info['bk_app_abbr'],
                                 **basic_info)
        return result

    def _save(self, json_config_path: str, content: str, file_type: Literal["md", "png", "html"]) -> str:
        filename = json_config_path.split('/')[-1].rstrip('.json')
        filepath = f'{config.workspace_root}/{filename}.{file_type}'
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
