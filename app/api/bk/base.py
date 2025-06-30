import json
from typing import Optional, Any, Dict

import aiohttp

from app.logger import logger
from app.exceptions import (
    ActionFailed, HttpFailed, NetworkError, TokenNotAvailable,
    ApiNotAvailable,
)
from app.api.base import Api

_token = {}  # type: Dict[str, Any]


class BKApi(Api):
    """
    Call Component APIs through HTTP.
    """

    def __init__(self,
                 api_root: Optional[str],
                 app_id: Optional[str],
                 app_secret: Optional[str],
                 *args, **kwargs):
        super(BKApi, self).__init__(api_root, *args, **kwargs)
        self.app_id = app_id
        self.app_secret = app_secret
        if not self._is_token_available():
            self._access_token = self._get_access_token()
            _token[self.app_id] = self._access_token
        else:
            self._access_token = _token[self.app_id]

    def _get_access_token(self) -> Dict:
        """
        Native version don't need access_token
        by use add appid to the white paper
        Outer version can update the db and
        add the appid the field
        """
        return {
            "X-Bkapi-Authorization": json.dumps({"bk_app_code": self.app_id,
                                                 "bk_app_secret": self.app_secret,
                                                 "bk_username": "bk_chat"})
        }

    def _is_token_available(self) -> bool:
        if self.app_id in _token:
            return True

        return False

    def _handle_api_result(self, result: Optional[Dict[str, Any]]) -> Any:
        if isinstance(result, dict):
            if result.get('result', False) or result.get('code', -1) == 0 or result.get('status', -1) == 0:
                return result.get('data')
            logger.error(result)
            raise ActionFailed(code=result.get('code'), info=result)

    async def call_action(self, action: str, method: str, **params) -> Any:
        if not self._is_available():
            raise ApiNotAvailable

        if not self._access_token:
            raise TokenNotAvailable

        url = f"{self._api_root}/{action}"
        if 'headers' in params:
            params['headers'].update(self._access_token)
        else:
            params['headers'] = self._access_token

        try:
            async with aiohttp.request(method, url, **params) as resp:
                if 200 <= resp.status < 300:
                    return self._handle_api_result(json.loads(await resp.text()))
                raise HttpFailed(resp.status)
        except aiohttp.InvalidURL:
            raise NetworkError('API root url invalid')
        except aiohttp.ClientError:
            raise NetworkError('HTTP request failed with client error')

    def _is_available(self) -> bool:
        return bool(self._api_root and self.app_id and self.app_secret)
