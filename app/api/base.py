import abc
import functools
from typing import Optional, Dict, Any, Callable, Literal


class Api:
    """
    API interface.
    """

    def __init__(self, api_root: str, *args, **kwargs):
        self._api_root = api_root

    def __getattr__(self, item: str) -> Callable:
        """
        Get a callable that sends the actual API request internally.
        """
        return functools.partial(self.call_action, item)

    @abc.abstractmethod
    def _get_access_token(self, token_root: str) -> Any:
        pass

    @abc.abstractmethod
    def _handle_api_result(self, result: Optional[Dict[str, Any]]) -> Any:
        pass

    @abc.abstractmethod
    async def call_action(self,
                          action: str,
                          method: Literal['POST', 'GET', 'PUT', 'DELETE'],
                          **params) -> Optional[Dict[str, Any]]:
        """
        Send API request to call the specified action.
        """
        pass

    @abc.abstractmethod
    def _is_available(self) -> bool:
        pass
