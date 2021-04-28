'''
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
'''
from etcd3.events import DeleteEvent, PutEvent
from .executor import get_executor
from concurrent import futures
import json
import logging
import uuid
import threading
import typing
from .constants import REXFLOW_ROOT
from .etcd_utils import get_etcd
from .executor import get_executor

'''
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

'''
TOKEN_POOL_NAME = 'pool_name'
TOKEN_SIZE = 'size'
TOKEN_AVAIL = 'avail'
TOKEN_ACTIVE = 'active'
TOKEN_ERROR = 'error'
TOKEN_COMPLETE = 'complete'
TOKEN_DONE = 'done'

def token_pool_key(pool_name : str) -> str:
    '''{REXFLOW_ROOT}/tokens/{self.wf_inst_id}'''
    return f'{REXFLOW_ROOT}/tokens/{pool_name}'

def token_make_pool_name(wf_inst_id : str) -> str:
    return f'{wf_inst_id}-{uuid.uuid4().hex}'

def token_create_pool(wf_instance_id : str, size : int) -> str:
    '''
    Creates a new token pool, and returns the name of the token pool. The name is
    prefixed with wf_instance_id with sufficient characters appended to make it
    unique among all other thread pools. The pool is initialized with the indicated
    number of tokens with the PENDING state.
    '''
    assert wf_instance_id is not None, 'workflow instance id is required'
    assert size > 0, 'pool size must be positive'

    pool_name = token_make_pool_name(wf_instance_id)
    # size - the number of tokens originvally created
    # avail - the number of token available
    # active - the number of tokens currently active
    # error - the number of tokens errored out
    # complete - the number of complete tokens
    # done - True if error + complete == size
    hive = {TOKEN_POOL_NAME: pool_name, TOKEN_SIZE: size, TOKEN_AVAIL:size, TOKEN_ACTIVE:0, TOKEN_ERROR:0, TOKEN_COMPLETE:0, TOKEN_DONE:False}
    key = token_pool_key(pool_name)
    etcd = get_etcd()
    etcd.put(key, json.dumps(hive))
    return pool_name

def token_get_pool(pool_name : str) -> typing.Dict[str,typing.Any]:
    key = token_pool_key(pool_name)
    etcd = get_etcd()
    with etcd.lock(key):
        hive = etcd.get(key)[0]
        return json.loads(hive)

def token_alloc(pool_name : str) -> None:
    key = token_pool_key(pool_name)
    etcd = get_etcd()
    with etcd.lock(key):
        hive = json.loads(etcd.get(key)[0])
        if hive[TOKEN_AVAIL] == 0:
            raise ValueError(f'No tokens availble for pool {pool_name}')
        hive[TOKEN_AVAIL]  -=  1
        hive[TOKEN_ACTIVE] +=  1
        logging.debug(f'Token alloced {pool_name} {hive}')
        etcd.put(key, json.dumps(hive))

def token_release(pool_name : str, bucket : str = TOKEN_COMPLETE) -> bool:
    assert bucket in [TOKEN_COMPLETE,TOKEN_ERROR], f'{bucket} is not a valid bucket - must be {TOKEN_ERROR} or {TOKEN_COMPLETE}'
    key  = token_pool_key(pool_name)
    etcd = get_etcd()
    with etcd.lock(key):
        hive = json.loads(etcd.get(key)[0])
        assert hive[TOKEN_ACTIVE] > 0, f'{pool_name} has ho active tokens'
        hive[TOKEN_ACTIVE] -= 1
        hive[bucket]       += 1
        hive[TOKEN_DONE] = hive[TOKEN_ERROR] + hive[TOKEN_COMPLETE] == hive[TOKEN_SIZE]
        etcd.put(key, json.dumps(hive))
        logging.debug(f'Token released {pool_name} {bucket} {hive}')
        return hive[TOKEN_DONE]
    return False

def token_fail(pool_name : str) -> typing.NoReturn:
    return token_release(pool_name, bucket=TOKEN_ERROR)

class TokenCompletionWatcher:
    '''
    This is meant to be used by a terminating event (end event, parallel gateway, etc)
    and will monitor the key pool(s) specified until all tokens are accounted for.

    Usage:
    w = TokenCompletionWatch(pool_ids)
    done_flag,results = w.start()  # blocking call - will not return until all events are processed
    '''
    def __init__(self, pool_ids):
        self.etcd = get_etcd()
        self.executor = get_executor()
        self.pool_ids = pool_ids
        self.futures = []
        self.cancels = []

    def start(self):
        for pool_id in self.pool_ids:
            self.futures.append(self.executor.submit(self.watch, pool_id))
        futures.wait(self.futures, return_when=futures.ALL_COMPLETED)
        results = {}
        all_done = True
        for pool_id in self.pool_ids:
            results[pool_id] = token_get_pool(pool_id)
            if not results[pool_id][TOKEN_DONE]:
                all_done = False
                break
        return [all_done, results]

    def stop(self):
        if self.cancels:
            for cancel_watch in self.cancels:
                cancel_watch()

    def watch(self, pool_id : str):
        pool_key = token_pool_key(pool_id)
        if token_get_pool(pool_id)[TOKEN_DONE]:
            logging.info(f'Watch on pool {pool_id} aborted because pool is already complete')
        else:
            watch_iter, cancel_watch = self.etcd.watch_prefix(pool_key)
            self.cancels.append(cancel_watch)
            for event in watch_iter:
                logging.info(event)
                cnts = token_get_pool(pool_id)
                logging.debug(f'{pool_id} Change detected S:{cnts[TOKEN_SIZE]} V:{cnts[TOKEN_AVAIL]} A:{cnts[TOKEN_ACTIVE]} E:{cnts[TOKEN_ERROR]} C:{cnts[TOKEN_COMPLETE]} D:{cnts[TOKEN_DONE]}')
                if cnts[TOKEN_DONE]:
                    break

if __name__ == "__main__":
    pool_name = token_create_pool('test_workflow_id', 10)
    hive = token_get_pool(pool_name)
    print(hive)
