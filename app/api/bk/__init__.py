from typing import List

from app.api.bk.base import BKApi
from app.api.bk.bkm import Bkmonitorv3
from app.api.bk.bkcmdb import Bkcmdb


class BKService:
    __slots__ = ['bkmonitorv3', 'bkcmdb']

    def __init__(self, product: List, api_root: str, app_id: str, app_secret: str):
        for item in product:
            api = BKApi(api_root=api_root.format(product=item),
                        app_id=app_id,
                        app_secret=app_secret)
            name = item.replace('-', '')
            setattr(self, name, globals()[name.title()](api))
