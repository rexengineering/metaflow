'''Experiments with persisted namespaces.
'''
from typing import Any

from pydantic import BaseModel

from flowlib.stores import KVStore


class PersistedModel:
    def __init__(self, model: BaseModel, backing_store: KVStore[Any]):
        self.__model = model
        self.__backing_store = backing_store
        self.__types__ = {
            name: value if isinstance(value, type) else type(value)
            for name, value in model.__annotations__.items()
        }

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError('Lazy developer error!')
        # return getattr(self.__model, name)
        # if name in self.__annotations__:
        #     result = self.__backing_store.get(name)
        #     if result is not None:
        #         return result
        #     else:
        #         return self.__annotations__[name]
        # raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        if name in self.__types__:
            expected_type = self.__types__[name]
            if isinstance(value, expected_type):
                self.__backing_store.set(name, value)
            else:
                raise ValueError(value)
        raise AttributeError(name)
