import json
import time
import csv
from typing import Any, Literal, List, Dict, Optional, Generator

from pydantic import Field, BaseModel, model_validator

from app.tool.base import BaseTool, ToolResult
from app.config import config
from app.api import BKService
from app.logger import logger
from app.exceptions import ToolError

_DI_GATHER_DATA_TOOL_DESCRIPTION = """
这是一个强大数据工具，擅长筛选与需求相关的数据表并查询详细指标，该工具提供数据表查询(list)，指标查询(query)等函数
1.从用户输入中抓出指标实体，可以数据表查询(list)的search参数的输入
2.生成结果为 drawer 和 analyst 工具提供标准化输入
"""


class DiListMetricMeta(BaseModel):
    id: int
    name: str
    metric_field: str
    result_table_id: str
    parameters: Dict
    dimensions: List

    def __str__(self):
        return f"- id: {self.id}\n" \
               f"  name: {self.name}\n" \
               f"  metric_field: {self.metric_field}\n" \
               f"  result_table_id: {self.result_table_id}\n" \
               f"  dimensions: {self.dimensions}"


class DiQueryDataMeta(BaseModel):
    datapoints: List
    json_config_path: str
    target: str
    unit: str = ""

    def __str__(self):
        return f"- target: {self.target}\n" \
               f"  json_config_path: {json.dumps(self.json_config_path)}"


class DiQueryDataResponse(ToolResult):
    """Structured response from di gather data tool, inheriting ToolResult."""
    results: Dict = Field(
        default_factory=dict, description="List of query metric"
    )
    metadata: Optional[DiQueryDataMeta] = Field(
        default=None, description="Metadata about the query metric"
    )

    @model_validator(mode="after")
    def populate_output(self) -> "DiQueryDataResponse":
        # todo maybe add a drawer here or transfer to csv/json
        if self.error:
            return self

        metrics = DiQueryDataMeta(target=self.metadata.target,
                                  datapoints=self.metadata.datapoints,
                                  json_config_path=self.metadata.json_config_path)
        self.output = f'Metric: \n {metrics}'
        return self


class DIGatherData(BaseTool):
    """
    这是一个强大数据工具，擅长筛选与需求相关的数据表并查询详细指标，该工具提供数据表查询(list)，指标查询(search)等函数
    """

    name: str = "gather_data"
    description: str = _DI_GATHER_DATA_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: list, query. "
                               "If you want to find a metric data, you can use the list command to find "
                               "the metric more related to the requirement, "
                               "then use the query command to get the detail data",
                "enum": [
                    "list",
                    "query",
                ],
                "type": "string",
            },
            "bk_biz_id": {
                "description": "The id of a business, the only key",
                "type": "integer",
            },
            "search": {
                "description": "The key metric text from user input. Optional for list command, "
                               "it can be use to filter metric, eg: 在线",
                "type": "string",
            },
            "data_type_label": {
                "description": "The data type of a series data. Required for list command",
                "enum": ["time_series"],
                "type": "string",
            },
            "page": {
                "description": "The offset of the list's metric_list response ."
                               "Optional for list command. Default value is 1",
                "type": "integer",
            },
            "page_size": {
                "description": "The limit of the item that list command will show. "
                               "Optional for list command. Default value is 1000",
                "type": "integer",
            },
            "end_time": {
                "description": "The end time of a metric datapoints, it's a timestamp,the unit is second. "
                               "Required for query command.",
                "type": "integer",
            },
            "start_time": {
                "description": "The start time of a metric datapoints, it's a timestamp,the unit is second. "
                               "Required for query command.",
                "type": "integer",
            },
            "metric_field": {
                "description": "The metric field come form list command response, eg: in_use."
                               "Required for query command.",
                "type": "integer",
            },
            "result_table_id": {
                "description": "The ID of a metric result table come form list command response, eg: system.disk."
                               "Required for query command.",
                "type": "integer",
            },
            "method": {
                "description": "The convergence method for result data, it is more like sql's method",
                "type": "string",
                "default": "AVG",
                "enum": ["SUM", "AVG", "MAX", "MIN", "COUNT"],
            },
        },
        "required": ["command", "bk_biz_id"],
    }

    metrics: List[Dict] = Field(default_factory=list, description="通过list函数获取到的指标列表")
    bk_service: BKService = None
    meaningless_dimensions: List[str] = [
        'bcs_cluster_id', 'bk_endpoint_index', 'bk_endpoint_url', 'bk_instance', 'bk_job', 'bk_monitor_name',
        'bk_monitor_namespace', 'bk_monitor_namespace/bk_monitor_name', 'bk_agent_id', 'devops_id',
    ]

    async def execute(self, command: Literal["list", "query"], bk_biz_id: int, **kwargs) -> Any:
        if config.bk_config is None:
            return ToolResult(output='bk config is not correct')

        bk_config = config.bk_config
        self.bk_service = BKService(bk_config.product,
                                    bk_config.api_root,
                                    bk_config.bk_app_code,
                                    bk_config.bk_app_secret)

        if command == "list":
            return await self._list(bk_biz_id, **kwargs)
        elif command == "query":
            return await self._query(bk_biz_id, **kwargs)
        else:
            raise ToolError(
                f"Unrecognized command: {command}. Allowed commands are: list, query"
            )

    async def _list(self,
                    bk_biz_id: int,
                    data_type_label: Literal["time_series"] = 'time_series',
                    page: int = 1,
                    page_size: int = 1000,
                    search: str = "",
                    **kwargs) -> ToolResult:
        """过滤出业务下所有的指标列表"""
        output = "可用的指标列表:\n"
        conditions = [{"key": "query", "value": search}] if search != "" else []
        self.metrics = await self.bk_service.bkmonitorv3.get_metric_list(bk_biz_id=bk_biz_id,
                                                                         page=page,
                                                                         page_size=page_size,
                                                                         data_type_label=data_type_label,
                                                                         conditions=conditions)
        logger.debug(f"metric count {self.metrics['count']}")
        for metric in self.metrics['metric_list']:
            parameters = {
                "bk_biz_id": bk_biz_id,
                "name": metric["name"],
                "start_time": "",
                "end_time": "",
                "query_configs": [
                    {
                        "data_source_label": "bk_monitor",
                        "data_type_label": "time_series",
                        "metrics": [
                            {
                                "field": metric['metric_field'],
                                "method": "AVG",
                                "alias": "a"
                            }
                        ],
                        "table": metric["result_table_id"],
                    }
                ]
            }
            dimensions = [d['id'] for d in metric['dimensions'] if d['id'] not in self.meaningless_dimensions]
            dm = DiListMetricMeta(id=metric['id'],
                                  name=metric['name'],
                                  result_table_id=metric['result_table_id'],
                                  metric_field=metric['metric_field'],
                                  parameters=parameters,
                                  dimensions=dimensions)
            output += f"{dm}\n"
        return ToolResult(output=output)

    async def _query(self,
                     bk_biz_id: int,
                     start_time: int,
                     end_time: int,
                     metric_field: str,
                     result_table_id: str,
                     method: Literal["SUM", "AVG", "MAX", "MIN", "COUNT"] = "AVG",
                     group_by: List[str] = None,
                     **kwargs) -> DiQueryDataResponse:
        """查询出业务下某个指标的时序数据并返回"""
        _start_time = start_time
        _end_time = end_time

        if _start_time is None or _end_time is None:
            _end_time = int(time.time())
            _start_time = _end_time - 3600

        _query_configs = [
            {
                "data_source_label": "bk_monitor",
                "data_type_label": "time_series",
                "metrics": [
                    {
                        "field": metric_field,
                        "method": method,
                        "alias": "a"
                    }
                ],
                "table": result_table_id,
                "group_by": group_by if group_by else []
            }
        ]

        payload = {
            "bk_biz_id": bk_biz_id,
            "expression": "a",
            "start_time": _start_time,
            "end_time": _end_time,
            "query_configs": _query_configs,
        }
        data = await self.bk_service.bkmonitorv3.time_series_unify_query(**payload)
        try:
            json_config_path = self._save(data, bk_biz_id)
            return DiQueryDataResponse(
                status="success",
                results=data,
                metadata=DiQueryDataMeta(datapoints=data['series'][0]['datapoints'],
                                         json_config_path=json_config_path,
                                         target=data['series'][0]['target'])
            )
        except (IndexError, ValueError):
            return DiQueryDataResponse(error='parse result error')

    @staticmethod
    def _datapoints2json(data: List[List]) -> Generator:
        """[[],[]] -> [{}]"""
        for item in data:
            s = time.localtime(item[1] / 1000)
            dt = time.strftime("%Y-%m-%d %H:%M:%S", s)
            yield {
                'value': item[0],
                'timestamp': dt
            }

    def _save(self, data: Dict, bk_biz_id: int) -> str:
        def _config(raw: Dict) -> Generator:
            for i, item in enumerate(raw['series']):
                datapoints, target, _type = item['datapoints'], item['target'], item['type']
                json_data = list(self._datapoints2json(datapoints))
                fieldnames = list(json_data[0].keys())

                csv_file_path = f"{config.workspace_root}/{target}.csv"
                with open(csv_file_path, 'w', newline='') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(json_data)

                metric = raw['metrics'][i]
                yield {
                    'csvFilePath': csv_file_path,
                    'chartTitle': f"{metric['result_table_id']} {target}'s {_type.title()}",
                    'chartType': _type,
                    'dimensions': [d['id'] for d in metric['dimensions'] if d['id'] not in self.meaningless_dimensions],
                    'insightsFilePath': f"{config.workspace_root}/visualization/{target}.md",
                    'chartFilePath': f"{config.workspace_root}/visualization/{target}.png",
                    'insights': f"{config.workspace_root}/visualization/{target}.json",
                    'name': metric['metric_field_name'],
                }
        if not data['series']:
            return None
        metadata = {
            "bk_biz_id": bk_biz_id,
            "config": list(_config(data))
        }
        json_config_path = f"{config.workspace_root}/{int(time.time())}.json"
        with open(json_config_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False)

        return json_config_path
