from typing import Dict

from app.api.bk.base import BKApi


class Bkmonitorv3:
    """
    BKMonitor V3 api shortcut
    """

    def __init__(self, bkm_api: BKApi):
        self.bkm_api = bkm_api

    async def get_metric_list(self, **kwargs) -> Dict:
        """
        - kwargs:
        {
            "conditions": [
                {
                    "key": "query",
                    "value": ""
                }
            ],
            "data_type_label": "time_series",
            "tag": "",
            "page": 1,
            "page_size": 20,
            "bk_biz_id": 100661
        }
        """
        return await self.bkm_api.call_action('get_metric_list/', 'POST', json=kwargs)

    async def time_series_unify_query(self, **kwargs) -> Dict:
        """
        - kwargs:
        {
            "bk_biz_id": 100661,
            "query_configs": [
                {
                    "data_source_label": "bk_monitor",
                    "data_type_label": "time_series",
                    "metrics": [
                        {
                            "field": "usage",
                            "method": "SUM",
                            "alias": "a"
                        }
                    ],
                    "table": "system.cpu_summary",
                    "data_label": "",
                    "index_set_id": null,
                    "group_by": [],
                    "where": [],
                    "interval": 60,
                    "interval_unit": "s",
                    "time_field": null,
                    "filter_dict": {},
                    "functions": []
                }
            ],
            "expression": "a",
            "alias": "a",
            "name": "SUM(CPU使用率)",
            "start_time": 1747921141,
            "end_time": 1747924741,
            "slimit": 500,
            "down_sample_range": "4s"
        }
        """
        return await self.bkm_api.call_action('time_series/unify_query/', 'POST', json=kwargs)
