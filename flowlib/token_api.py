"""
Manages a pool of tokens stored in a backstore (currently etcd) and provides
life-cycle management for those tokens.

Token life-cycle:

AVAIL -> ACTIVE -+-> COMPLETE
                 +-> LOST

TokenPool.create(iid:str, size:int) -> str
    Creates a new thread pool, and returns the name of the thread pool. The name is
    prefixed with wf_instance_id with sufficient characters appended to make it
    unique among all other thread pools. The pool is initialized with the indicated
    number of tokens.

TokenPool.alloc()
    Allocates one token by moving it from the AVAIL bucket to the ACTIVE bucket.

TokenPool.release_as_complete()
    Releases one token by moving it from the ACTIVE bucket to the COMPLETE bucket

TokenPool.release_as_lost()
    Releases one token by moving it from the ACTIVE bucket to the LOST bucket

pool_name = token_create_pool( wf_instance_id, 10 ) // create a pool of 10 tokens
token = token_alloc(pool_name, TokenState.RUNNING)  // pull a token from the pool and set state to RUNNING

The token is passed in the headers of the workflow, and is used by the terminating event. This is
usually an end event, but can be any intermediate event or task if it fails to pass control to
the next entity in the workflow. In this case, having only the token identifier, it needs to be
able to report the token as FAILED.

So, the terminating event needs to do two things:
1. Set the incoming token state to COMPLETE
2. Test if all tokens have been processed, and if so, terminate the workflow.
Because there can be multiple token pools in play during a given workflow instance, the
header contains a list of token id's.

tokens = headers['x-rexflow-tokens'].split(',')
alldone = True
for token in tokens:
    token_set_state(token, TokenState.COMPLETE)
    alldone = alldone and token_get_token_counts(token)[TokenCounts.DONE_FLAG]
if alldone:
    # okay to proceed/complete the workflow
"""
from enum import Enum
from etcd3.events import DeleteEvent, PutEvent
from concurrent import futures
import json
import logging
import uuid
import threading
import typing
from .constants import REXFLOW_ROOT
from .etcd_utils import get_etcd, locked_call

"""
workflow id is akin to conditional-8c6be6a5
workflow instance id is akin to conditional-8c6be6a5-7fb4eea885c111eb944ca2a57a5ac2db
token pool id is akin to conditional-8c6be6a5-7fb4eea885c111eb944ca2a57a5ac2db-98723984723983fff
                         <-- workflow id --->                                |                 |
                         <-- workflow instance id --------------------------->                 |
                         <-- workflow instance token pool ------------------------------------->
given a token, and split('-') results,
len(token.split('-')) == 2 : workflow-id
                         3 : workflow instance id
                         4 : workflow instance token pool id

{"count":3, "avail":3, "alloc":0, "error":0, "complete":0, "done":False}

token_alloc - moves 1 from avail to alloc
token_release - moves 1 from alloc to complete
token_error - moves 1 from alloc to error

"""
class TokenPool:
    SIZE_UNBOUNDED = -1

    def __init__(self, name:str, size:int):
        self.name     = name
        self.size     = size
        self.avail    = size
        self.active   = 0
        self.lost     = 0
        self.complete = 0

    @property
    def bounded(self):
        return self.size != TokenPool.SIZE_UNBOUNDED

    def get_name(self) -> str:
        return self.name

    def is_done(self) -> bool:
        return self.bounded and self.size == self.lost + self.complete

    def alloc(self):
        if self.bounded:
            assert self.avail > 0, f'{self.name} has no available tokens'
            self.avail -= 1
        self.active += 1
        self.write()

    def release_as_complete(self) -> bool:
        assert self.active > 0, f'{self.name} has no active tokens'
        self.active -= 1
        self.complete += 1
        self.write()
        return self.is_done()

    def release_as_lost(self) -> bool:
        """
        Lost is special case. This occurs when the timer is not able to fire its
        outside edge. In this case, a token was never allocated but nevertheless
        be accounted for. So we move a token from the avail bucket to the lost
        bucket directly.
        """
        if self.bounded:
            assert self.avail > 0, f'{self.name} has no available tokens'
            self.avail -= 1
        self.lost += 1
        self.write()
        return self.is_done()

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    def __str__(self):
        return f'{self.name} size:{self.size} aval:{self.avail} ' \
            f'actv:{self.active} lost:{self.lost} ' \
            f'cplt:{self.complete} done:{self.is_done()}'

    @classmethod
    def create(cls, iid:str, size:int):
        name = cls.pool_name(iid)
        pool = TokenPool(name, size)
        pool.write()
        return pool

    @classmethod
    def from_json(cls, jayson:str):
        if jayson is None:
            return None
        obj = TokenPool(None,0)
        hive = json.loads(jayson)
        for k,v in hive.items():
            setattr(obj, k, v)
        return obj
    @classmethod
    def key(cls, name:str) -> str:
        """{REXFLOW_ROOT}/tokens/{self.wf_inst_id}"""
        return f'{REXFLOW_ROOT}/tokens/{name}'

    @classmethod
    def pool_name(cls, iid:str) -> str:
        return f'tk-{iid}-{uuid.uuid4().hex[:12]}'

    @classmethod
    def from_pool_name(cls, name:str):
        key = TokenPool.key(name)

        def __logic(etcd):
            return etcd.get(key)[0]

        hive = locked_call(key, __logic)
        if hive is not None:
            return TokenPool.from_json(hive)
        return None

    @classmethod
    def erase(cls, name:str):
        key = cls.key(name)

        def __logic(etcd):
            etcd.delete(key)

        locked_call(key, __logic)

    def write(self):
        key = self.key(self.name)
        hive = self.to_json()

        def __logic(etcd):
            return etcd.put(key, hive)

        return locked_call(key, __logic)

if __name__ == "__main__":
    pool = TokenPool.create('test_workflow_id', 10)
    print(pool)
    pool.alloc()
    pool.release_as_lost()
    print(pool)
    pool.alloc()
    pool.release_as_complete()
    print(pool)
    while not pool.is_done():
        pool.alloc()
        pool.release_as_complete()
        print(pool)
    print(pool)
