'''Abstraction layer for persistent stores.
'''
import json
import pickle
from typing import Any, Iterator, MutableMapping, Optional, Type, TypeVar, Union

from etcd3 import Etcd3Client

from . import etcd_utils


class Codec:
    codec_obj: Any

    @classmethod
    def dumps(cls, value: Any, *args, **kws) -> bytes:
        return cls.codec_obj.dumps(value, *args, **kws)

    @classmethod
    def loads(cls, encoded: bytes, *args, **kws) -> Any:
        return cls.codec_obj.loads(encoded, *args, **kws)


class JSONCodec(Codec):
    codec_obj = json


class PickleCodec(Codec):
    codec_obj = pickle


Codecs = Union[Type[Codec], Codec]


VT = TypeVar('VT') # Value domain

class KVStore(MutableMapping[str, VT]):
    def set(self, key: str, value: VT) -> None:
        self[key] = value


class InMemoryStore(dict, KVStore):
    pass


ET = TypeVar('ET') # Etcd3Store value domain


class Etcd3Store(KVStore[ET]):
    def __init__(
        self,
        prefix: Optional[str] = None,
        codec: Optional[Codecs] = None,
        etcd_client: Optional[Etcd3Client] = None
    ):
        self.prefix = prefix if prefix is not None else ''
        self.codec: Codecs = codec if codec is not None else JSONCodec
        self.etcd_client: Etcd3Client = etcd_client if etcd_client is not None else etcd_utils.get_etcd()

    def __delitem__(self, key: str) -> None:
        self.etcd_client.delete(f'{self.prefix}{key}'.encode())

    def __getitem__(self, key: str) -> ET:
        data, _ = self.etcd_client.get(f'{self.prefix}{key}'.encode())
        if data is None:
            raise KeyError(f"'{key}'")
        return self.codec.loads(data)

    def _get_keys(self):
        if len(self.prefix) > 0:
            return self.etcd_client.get_prefix(self.prefix.encode(), keys_only=True)
        else:
            return self.etcd_client.get_all(keys_only=True)

    def __iter__(self) -> Iterator[str]:
        return iter(metadata.key.decode() for _, metadata in self._get_keys())

    def __len__(self) -> int:
        return len(list(self._get_keys()))

    def __setitem__(self, key: str, value: ET) -> None:
        self.etcd_client.put(f'{self.prefix}{key}'.encode(), self.codec.dumps(value))
