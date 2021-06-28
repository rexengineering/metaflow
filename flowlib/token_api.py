"""
Manages a pool of tokens stored in a backstore (currently etcd) and provides
life-cycle management for those tokens.

Token life-cycle:

PENDING -> RUNNING -+-> COMPLETE
                    +-> FAILED

token_create_pool(wf_instance_id : str, size : int) -> str
    Creates a new thread pool, and returns the name of the thread pool. The name is
    prefixed with wf_instance_id with sufficient characters appended to make it
    unique among all other thread pools. The pool is initialized with the indicated
    number of tokens.

token_alloc(pool_name : str) -> str

token_release(pool_name : str, state : TokenState = None) -> str

token_get_token_counts(pool_name : str) -> list[int]
    Valid keys are members of the TokenCounts class:
        TokenCounts.POOL - the guid of the token pool (workflow instance id)
        TokenCounts.SIZE - the size of the token pool
        TokenCounts.PENDING - the number of tokens in PENDING state
        TokenCounts.RUNNING - the number of tokens in RUNNING state
        TokenCounts.FAILED - the number of tokens in FAILED state
        TokenCounts.COMPLETE - the number of tokens in COMPLETE state
        TokenCounts.DONE_FLAG - True if TokenCounts.COMPLETE + TokenCounts.FAILED == TokenCounts.SIZE

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
# from .executor import get_executor

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

class TokenPoolBucket(Enum):
    BUCKET_COMPLETE = 0
    BUCKET_LOST     = 1
    BUCKET_ERROR    = 2

class TokenPool:
    def __init__(self, name:str, size:int):
        self.name = name
        self.size = size
        self.avail = size
        self.active = 0
        self.lost = 0
        self.error = 0
        self.complete = 0

    def get_name(self) -> str:
        return self.name
    
    def is_done(self) -> bool:
        return self.size == self.lost + self.error + self.complete

    def alloc(self):
        assert self.avail > 0, f'{self.name} has no available tokens'
        self.avail  -= 1
        self.active += 1
        self.write()

    def __release(self, bucket:TokenPoolBucket = TokenPoolBucket.BUCKET_COMPLETE) -> bool:
        assert self.active > 0, f'{self.name} has no active tokens'
        self.active -= 1
        if bucket == TokenPoolBucket.BUCKET_COMPLETE:
            self.complete += 1
        elif bucket == TokenPoolBucket.BUCKET_LOST:
            self.lost += 1
        else: #bucket == TokenPoolBucket.BUCKET_ERROR:
            self.error += 1
        self.write()
        return self.is_done()

    def set_lost(self) -> bool:
        return self.__release(TokenPoolBucket.BUCKET_LOST)
    
    def set_complete(self) -> bool:
        return self.__release(TokenPoolBucket.BUCKET_COMPLETE)

    def set_error(self) -> bool:
        return self.__release(TokenPoolBucket.BUCKET_ERROR)
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    def __str__(self):
        return f'{self.name} size:{self.size} avail:{self.avail} ' \
            f'activ:{self.active} lost:{self.lost} err:{self.error} ' \
            f'cplt:{self.complete} done:{self.is_done()}'
    
    @classmethod
    def create(cls, iid:str, size:int):
        name = cls.pool_name(iid)
        pool = TokenPool(name, size)
        pool.write()
        return pool

    @classmethod
    def from_json(cls, jayson:str):
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
    def read(cls, name:str):
        key = TokenPool.key(name)

        def __logic(etcd):
            return etcd.get(key)[0]

        hive = locked_call(key, __logic)
        return TokenPool.from_json(hive)

    def write(self):
        key = self.key(self.name)
        hive = self.to_json()

        def __logic(etcd):
            return etcd.put(key, hive)

        return locked_call(key, __logic)

if __name__ == "__main__":
    pool = TokenPool.create('test_workflow_id', 10)
    print(pool)
    pool.set_error()
    print(pool)
    pool.alloc()
    pool.set_lost()
    print(pool)
    pool.alloc()
    pool.set_complete()
    print(pool)
    while not pool.is_done():
        pool.alloc()
        pool.set_complete()
        print(pool)
    print(pool)
