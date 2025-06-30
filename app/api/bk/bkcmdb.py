from typing import Dict

from app.api.bk.base import BKApi


class Bkcmdb:
    """
    bk-cmdb api shortcut
    """

    def __init__(self, cc_api: BKApi):
        self.bk_cmdb_api = cc_api

    async def search_business(self, **params) -> Dict:
        """
        -params:
        "condition": {
            "bk_biz_id": xxx
        }
        """
        return await self.bk_cmdb_api.call_action('api/v3/biz/search/tencent', 'POST', json=params)
