"""
Contains framework logic for processing timed events.

ISO 8601 formats are supported by the standard python library

persistance - whenever a timed event is created, it is persisted in a database
              and all events are read in on startup as a recovery method.

              Restored events that have passed their maturity time are processed
              according to workflow options. Cycle timers will have their next
              timer scheduled accordingly.

events are stored in the and etcd workflow hive.
/rexflow/workflows/<workflow_id>/timed_events/<instance_id>
The value is a JSON'd list of

    {
        'type' : 'timerDate',                           # timeDate / timeCycle / timeDuration
        'spec' : 'P10D',                                # ISO 8610 code apropos to type
        'max_rep' : '10',                               # number of repetitions - 0 for infinite
        'rep': '0',                                     # the current reps we've run
        'data' : [data, flow_id, wf_id, content_type]   # outbound event data
    }

"""
from flowlib.etcd_utils import (
    locked_call, 
    get_keys_from_prefix,
    get_etcd,
)
from multiprocessing import Lock
import isodate
import json
import logging
import threading
import time
import typing
import uuid

from enum import Enum
from datetime import datetime, timezone
from flowlib.constants import WorkflowKeys, split_key
from flowlib.executor import get_executor
from flowlib.substitution import Substitutor, Tokens
from flowlib.token_api import TokenPool

from typing import Callable, Tuple, Union

class TimerErrorCode(Enum):
    TIMER_ERROR_FAIL_IID = 'timerErrorFailInstance'

class TimeUtc:
    @classmethod
    def now(cls):
        return int(datetime.now(timezone.utc).timestamp())

    @classmethod
    def format_8601(cls,ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(Literals.ISO_8601_FORMAT)

    @classmethod
    def now_str(cls):
        return cls.format_8601(cls.now())

class TimerType(Enum):
    TIME_DATE      = 'timeDate'
    TIME_DURATION  = 'timeDuration'
    TIME_CYCLE     = 'timeCycle'

    def __str__(self):
        return self.name

class TimerRecoveryPolicy(Enum):
    """
    The timer recovery policy. If a pod dies with active timers, this
    policy defines the behavior for how events that *should* have fired
    in the past are handled once the timers are loaded from the back store.
    RECOVER_FORGET - ignore past events (mark them as ignored in token pool)
    RECOVER_FIRE   - fire all past events immediately
    RECOVER_FAIL   - (default) fail the workflow instance
    RECOVER_FUTURE - (not implemented) schedule them in the future with now() as base time
    """
    RECOVER_FORGET = 'forget'
    RECOVER_FIRE   = 'fire'
    RECOVER_FAIL   = 'fail'
    # RECOVER_FUTURE = 'future'

class Recurrence:
    NOREPEAT  =  0
    UNBOUNDED = -1
    UNBOUNDED_INTERVAL = 60 # seconds

class Literals:
    ADD_FUNC = 'ADD'
    SUB_FUNC = 'SUB'
    NOW_FUNC = 'NOW'
    ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

class Functions:
    """
    Functions for Substitutor defined here in global scope
    """
    @classmethod
    def _time_preproc(cls, parms:str) -> list:
        args = []
        for arg in parms.split(','):
            val = TimedEventManager.parse_spec(arg)[1][0]
            args.append(val)
        return args

    @classmethod
    def func_add(cls, parms:str) -> str:
        """Add two time elements"""
        args = cls._time_preproc(parms)
        assert len(args) == 2, f'{Literals.ADD_FUNC} takes 2 parameters, {len(args)} provided'
        args[0] += args[1]
        return TimeUtc.format_8601(args[0])

    @classmethod
    def func_sub(cls, parms:str) -> str:
        """Subtract two time elements"""
        args = cls._time_preproc(parms)
        assert len(args) == 2, f'{Literals.SUB_FUNC} takes 2 parameters, {len(args)} provided'
        args[0] -= args[1]
        return TimeUtc.format_8601(args[0])

    @classmethod
    def func_now(cls, parms:str = None) -> str:
        """Return now utc as ISO-8601 formatted timestamp"""
        # NOW() takes no arguments, returns the curent date/time as ISO_8601_FORMAT
        return TimeUtc.now_str()

class ValidationResults(Recurrence):
    def __init__(self, timer_type:str, spec:str):
        self.timer_type = TimerType(timer_type)
        self.spec       = spec
        self.start_date = None
        self.end_date   = None
        self.interval   = 0
        self.recurrence = 0

    @property
    def unbounded(self):
        return self.recurrence == Recurrence.UNBOUNDED

    @property
    def norepeat(self):
        return self.recurrence == Recurrence.NOREPEAT

    @property
    def is_cycle(self):
        return self.timer_type == TimerType.TIME_CYCLE

    @property
    def is_duration(self):
        return self.timer_type == TimerType.TIME_DURATION

    @property
    def is_date(self):
        return self.timer_type == TimerType.TIME_DATE

class TimedEventManager:
    """Forward declaration"""
    pass

class TimerContext(ValidationResults):
    """Forward declaration"""
    pass

class TimerContext(ValidationResults):
    """
    The context owned by a series of WrappedTimer objects to track its state
    and progress through the timer life cycle.
    """
    def __init__(self, source:ValidationResults, iid:str, token_stack:str, args:list):
        self.guid          = uuid.uuid4().hex
        self.iid           = iid
        self.timer_type    = source.timer_type
        self.start_date    = source.start_date
        self.end_date      = source.end_date
        self.interval      = source.interval
        self.recurrence    = source.recurrence
        self.spec          = source.spec
        self.token_stack   = token_stack
        self.exec_time     = 0
        self.token_pool_id = None
        self.args          = args
        self.completed     = False
        self.did,_         = split_key(self.iid)
        self.key           = f'{WorkflowKeys.timed_events_key(self.did)}/{self.iid}'

    @property
    def continues(self):
        """
        Answer whether a timeCycle timer should continue
        """
        return self.is_cycle and (self.unbounded or self.recurrence > 0)

    def decrement(self):
        """
        Decrement the recurrence counter if apropos for this timer type.
        Return True if recurrence counter is zero
        """
        if self.is_cycle and not self.unbounded and self.recurrence > 0:
            self.recurrence -= 1
            return self.recurrence == 0
        return False

    def to_json(self) -> str:
        ret = {k:v for k,v in self.__dict__.items() if not k.startswith('__')}
        ret['timer_type'] = ret['timer_type'].name
        args = []
        for v in ret['args']:
            if isinstance(v,bytes):
                v = v.decode()
            args.append(v)
        ret['args'] = args
        return json.dumps(ret)

    def save(self):
        logging.info(f'Saving timer {self.guid}')
        data = self.to_json()
        def __logic(etcd):
            etcd.put(self.key,data)
        locked_call(self.key,__logic)

    @classmethod
    def erase(cls, key):
        logging.info(f'Erasing timer {key}')
        def __logic(etcd):
            etcd.delete(key)
        locked_call(key, __logic)

    @classmethod
    def from_json(cls, jayson:Union[str, bytes, dict]) -> TimerContext:
        if isinstance(jayson,str):
            data = json.loads(jayson)
        elif isinstance(jayson,bytes):
            data = json.loads(jayson.decode())
        elif isinstance(jayson,dict):
            data = jayson
        else:
            raise ValueError('cannot interpret input to from_json')
        obj = cls.__new__(cls) # does not call __init__
        for k,v in data.items():
            if k == 'timer_type':
                v = TimerType[v]
            setattr(obj,k,v)
        return obj

    @classmethod
    def restore(cls, iid) -> TimerContext:
        did,_ = split_key(iid)
        key   = f'{WorkflowKeys.timed_events_key(did)}/{iid}'
        return cls.restore_from_key(key)

    @classmethod
    def restore_from_key(cls, key):
        def __logic(etcd):
            data, _ = etcd.get(key)
            if data is not None:
                return cls.from_json(data)
            return None

        ctx = locked_call(key,__logic)
        if ctx is None:
            logging.info(f'Timer {key} could not be restored')
            cls.erase(key)
        else:
            logging.info(f'Loaded timer {ctx.guid} from storage')
        return ctx

from typing import Tuple

class WrappedTimer:
    """
    Python timers are created, start, and die without any notifications. This
    class wraps a threading.Timer object so that we can receive a notification
    once the timer matures.
    """
    def __init__(self, mgr:TimedEventManager, interval:int, done_action:Callable[[object],None], action:Callable[[list],None], context:TimerContext):
        self.mgr = mgr
        self._interval = interval
        self._done_action = done_action
        self._action = action
        self._context = context
        self._timer = threading.Timer(interval, self.do_action, context.args)
        logging.info(f'{time.time()} Timer created with duration {interval}')

    def do_action(self, *args):
        token_stack = None
        if self._context.token_pool_id is not None:
            tp = TokenPool.from_pool_name(self._context.token_pool_id)
            assert tp is not None, f'{self._context.guid} No token pool with name {self._context.token_pool_id}'
            tp.alloc()
            # need to pass the token_pool_id as an x header
            if self._context.token_stack is None or not self._context.token_stack:
                token_stack = []
            else:
                token_stack = list(self._context.token_stack.split(','))
            token_stack.append(self._context.token_pool_id)
            token_stack = ','.join(token_stack)

        abort = not self._action(self._context, *[token_stack, *args])
        if abort:
            # the call to the outside edge failed. Hence we need to
            # end any attempt at more timers.
            logging.error(f'{self._context.guid} failed to notify outbound edge - aborting')
        self.done(abort)

    def start(self):
        self._timer.start()
        self._context.save()
        logging.info(f'{self._context.guid} {TimeUtc.now()} Starting timer will execute {TimeUtc.format_8601(self._context.exec_time)}')

    def cancel(self):
        logging.info(f'{self._context.guid} {TimeUtc.now()} Canceling timer')
        self._timer.cancel()
        self.done()

    def done(self, abort:bool = False):
        logging.info(f'{self._context.guid} {TimeUtc.now()} Timer done')
        self._done_action(self._context, abort)

class TimedEventManager:
    """
    """
    def __init__(self,
            did:str,
            timer_desc:str,
            callback:Callable[[list], None],
            err_cb:Callable[[list],None],
            recovery_policy:str,
            is_start_event:bool = False):
        self.did = did
        self.json = timer_desc
        #[timer_type, timer_spec]
        self.timer_type, self.spec = json.loads(timer_desc)
        self.callback = callback
        self.err_callback = err_cb
        # convert recovery_policy into it's Enum equiv - if invalid let it raise
        self.recovery_policy = TimerRecoveryPolicy[recovery_policy.upper()]
        self.is_start_event = is_start_event
        # if validate_spec returns None, then the spec has dynamic references
        # i.e. {substitutions} and/or FUNCTIONS(), so we will resolve dynamically
        # in create_timer().
        self.aspects, self.is_dynamic_spec = TimedEventManager.validate_spec(self.timer_type, self.spec.upper())
        self.token_pool_id = None
        self.completed = True
        self._substitutor = Substitutor() \
            .add_handler(Literals.ADD_FUNC, Functions.func_add) \
            .add_handler(Literals.SUB_FUNC, Functions.func_sub) \
            .add_handler(Literals.NOW_FUNC, Functions.func_now)

        self.executor = get_executor()
        self.future = self.executor.submit(self.__restore_latent_timers)


    def reset(self, aspects:ValidationResults) -> None:
        """
        Reset the timer manager to the provided timer type and specification.
        This can only happen if the current configuration has already run its
        course.
        """
        assert self.completed, 'Cannot reset - timer still active'
        self.aspects = aspects

    def signal_error(self, context:TimerContext, code:TimerErrorCode, message:str):
        """
        Call the error callback
        """
        if self.err_callback:
            logging.error(f'Raising error {TimeUtc.now_str()} {context.guid} {code.name} {message}')
            # timer_error_callback(self, iid:str, code:TimerErrorCode, message:str):
            self.err_callback(context.iid, code, message)

    @classmethod
    def validate_spec(cls, timer_type : str, spec : str) -> Tuple[ValidationResults, bool]:
        logging.info(f'Validating {timer_type} {spec}')
        # check here if spec contains any substitution or function markers.
        # if so, return None
        if any( marker in [Tokens.FUNC_BEG, Tokens.SUBS_BEG] for marker in spec):
            logging.info('Deferring spec validation as spec has substitution/function markers')
            return None, True

        # the spec contains the ISO 8601 value apropos to type
        results = ValidationResults(timer_type, spec)

        # all times must be in GMT (Zulu)
        # either a specific datetime or a duration must be specified
        # infinite recurrences are not allowed i.e. R/PT10H or R0/PT10H
        #
        # The number of seconds in 100 years is 3,155,695,200 seconds
        # which is way under the upper bound of an int in python 3, so
        # we're safe converting all fixed and relative times into
        # seconds.
        if results.timer_type == TimerType.TIME_DATE:
            # spec needs to be an ISO 8601 date/time to execute
            # e.g. 2011-03-11T12:13:14Z
            try:
                results.start_date = int(isodate.parse_datetime(spec).timestamp())
                logging.info(f'timeDate timing event created - executing on {datetime.fromtimestamp(results.start_date, tz=timezone.utc)}')
            except Exception:
                raise ValueError(f'Invalid specification {spec}')

        elif results.timer_type == TimerType.TIME_DURATION:
            # spec needs to be an ISO 8601 period
            # e.g. P10D or PT33H
            try:
                assert spec.startswith('P'), 'timeDuration timed events must begin with \'P\''
                results.interval = int(isodate.parse_duration(spec).total_seconds())
                logging.info(f'timeDuration timing event created - {results.interval} seconds')
            except Exception:
                raise ValueError(f'Invalid specification {spec}')

        else: # results.is_cycle
            # spec need to be an ISO 8601 Repeating Interval
            # e.g. R3/PT10H
            assert spec.startswith('R'), 'Cycle timed events must begin with R'
            assert '/' in spec, 'Cycle timed events must provide recurrence and duration'
            toks = cls.parse_spec(spec)
            pat = toks[0]
            # acceptable patterns are RP, RPD, RDP, and RDD
            # RP  - recurrence and interval
            # RPD - recurrence, interval, end date
            # RDP - recurrence, start date, and interval
            # RDD - recurrence, start date, end date
            #
            # For each of the paterns that include dates, we need to determine the
            # start date, end date, and the interval between the two.
            # - If a start date is provided, it is the first event fired
            # - If an end date is provided, it is the last event fired
            # - If recurrences are > 2, then the period between the start-and-end
            #   dates is equally divided so that each event is fired at equal
            #   intervals.
            # - For unbounded events, the granularity is specified in
            #   Recurrence.UNBOUNDED_INTERVAL (currently 60 secs), and events are
            #   fired continuously starting on the start date through and including
            #   the end date.
            # For unbounded RP, the event fires every P without end. Hence the
            # workflow instance will never complete.

            assert pat in ['RP','RPD','RDP','RDD'], 'Improper cycle definition'
            datum = toks[1]
            results.recurrence = datum[0]
            if pat == 'RP':
                results.interval = datum[1]
                logging.info(f'timeCycle timing event created - {results.recurrence} cycle(s) '
                             f'{results.interval} seconds apart')

            elif pat == 'RDP':
                """
                recurrence/date/period
                """
                results.start_date = datum[1]
                results.interval   = datum[2]
                logging.info(f'timeCycle timing event created - {results.recurrence} cycle(s) '
                             f'{results.interval} seconds apart '
                             f'starting on {datetime.fromtimestamp(results.start_date, tz=timezone.utc)}')

            elif pat == 'RPD':
                """
                recurrence/period/end-date
                """
                results.interval = datum[1]
                results.end_date = datum[2]
                if results.unbounded:
                    # for unbounded period/end-date the start date end-date less period
                    results.start_date = results.end_date - results.interval
                    results.recurrence = int(results.interval / Recurrence.UNBOUNDED_INTERVAL)
                    results.interval   = Recurrence.UNBOUNDED_INTERVAL
                else:
                    if results.norepeat:
                        # for non-repeat recurrences the recurrence count is 2 for start/end
                        results.recurrence = 2
                    # otherwise, calculate the number of recurrences and subtract
                    # from end-date to get the start-date
                    results.start_date = results.end_date - (results.interval * results.recurrence)

                logging.info(f'timeCycle timing event created - {results.recurrence} cycle(s) '
                             f'{results.interval} seconds apart '
                             f'starting on {datetime.fromtimestamp(results.start_date, tz=timezone.utc)} '
                             f'ending on {datetime.fromtimestamp(results.end_date, tz=timezone.utc)}')

            else: # pat == 'RDD'
                # first event fires at start date
                # last event fires at end date
                # calculate the duration as (end - start) / (recurrence - 1)
                assert results.unbounded or results.norepeat or results.recurrence > 0, \
                    f'Invalid recurrence specified {results.recurrence}'
                results.start_date = datum[1]
                results.end_date   = datum[2]
                assert results.start_date < results.end_date, "Error - start date must preceed end date"
                period = results.end_date - results.start_date
                # unbounded the granularity is 60 secs.
                if results.unbounded:
                    results.interval   = Recurrence.UNBOUNDED_INTERVAL
                    results.recurrence = int(period/results.interval) + 1
                elif results.norepeat:
                    # essentually R0 and R1 are identical
                    results.recurrence = 1
                else:
                    results.interval = int(period / (results.recurrence - 1))

                logging.info(f'timeCycle timing event created - {results.recurrence} cycle(s) '
                             f'starting on {datetime.fromtimestamp(results.start_date, tz=timezone.utc)} '
                             f'ending on {datetime.fromtimestamp(results.end_date, tz=timezone.utc)} '
                             f'with interval {results.interval}'
                )

        return results, False

    @classmethod
    def parse_spec(cls, spec : str) -> list:
        """
        Parse the time period specification as per ISO 8601-1
        - elements are separated by '/' (4.4.2.a)
        - element that start with 'P' is a PERIOD (4.4.2.b)
        - element that starts with 'R' is a RECURRANCE (4.5.2)
        - otherwise the element is parsed as a DATETIME (4.3)

        Return a tuple of a pattern of encountered data elements, e.g.
        'RP' for a recurrence/period, and a list of result objects,
        e.g. ['RP',[3,103420]]
        """
        cat = ''
        results = []
        for elem in spec.strip().upper().split('/'):
            if elem.startswith('P'):
                # PERIOD
                cat += 'P'
                val = int(isodate.parse_duration(elem).total_seconds())
            elif elem.startswith('R'):
                # RECURRANCE
                cat += 'R'
                val = int(elem[1::]) if len(elem) > 1 else Recurrence.UNBOUNDED 
            else:
                # DATETIME
                cat += 'D'
                val = int(isodate.parse_datetime(elem).timestamp())
            results.append(val)

        return [cat,results]

    def create_timer(self, iid : str, token_stack : str, args : list):
        """
        The parms passed to us *must* be passed to the callback when firing the
        timer. Here, we take the timer parameters when the manager was created
        and determine the appropriate duration(s) for the timers to be created.

        timeDate - This is a fixed point in time. Policy is that if the date
                   has already passed, then fire the event immediately. This
                   might be changed ITMF by a globl workflow policy, with
                   local overrides.

        timeDuration - Simplest. Just wait the indicated number of seconds
                   before firing the event.

        timeCycle - Most confusing. Fire the event once ever so often, in
                   equal durations, up to a maximum number of times. This
                   is confusing in the rexflow implementation as to what the
                   behavior should be. For now, the event will be fired
                   every time the timer matures.
        """

        # if self.is_dynamic_spec is True, then we need to validate the spec employing
        # information passed in with the request
        if self.is_dynamic_spec:
            # args[0] is the data provided with the incoming request. This should be
            # JSON. So, decode that, and pass it to the substiution logic to get a
            # "current" timer specification, then validate that. Oy.
            req_json        = json.loads(args[0].decode())
            adj_spec        = self._substitutor.do_sub(req_json, self.spec)
            self.aspects, _ = self.validate_spec(self.timer_type, adj_spec)

        context = TimerContext(self.aspects, iid, token_stack, args)

        time_now = TimeUtc.now()
        # if a start_date was supplied, fire the first event on that date.
        if context.start_date is not None:
            if context.start_date < time_now:
                # start time is in the past
                duration = 0
            else:
                duration = context.start_date - time_now
        else:
            context.start_date = time_now
            duration = context.interval

        # the exec_time should be the point in time the event should fire
        context.exec_time = context.start_date + duration
        if context.exec_time < time_now:
            # TODO: enforce recovery policy
            logging.info(f'{context.guid} Timer {context.exec_time} occurs in the past - firing immediately')
            duration = 0

        if context.is_cycle:
            if not self.is_start_event:
                # cycle types need a token pool for remote collectors/end events to keep track of the number
                # of recurrences seen.
                context.token_pool_id = TokenPool.create(iid, context.recurrence).get_name()
                logging.info(f'{context.guid} Created token pool {context.token_pool_id}')
            context.decrement()

        print(context.to_json())

        self.completed = False
        timer = WrappedTimer(self, duration, self.__timer_done_action, self.__timer_action, context)
        timer.start()

    def __restore_latent_timers(self):
        """
        Pull any existing timer context records.
        """
        key = WorkflowKeys.timed_events_key(self.did)
        keys = get_keys_from_prefix(key)
        if keys is not None and len(keys) > 0:
            logging.info(f'Attempting to restore {len(keys)} timers from storage')
            for k in keys:
                ctx = TimerContext.restore_from_key(k)
                if ctx is not None:
                    self.restore_timer(ctx)
        else:
            logging.info('No timers found to restore')

    def restore_timer(self, context:TimerContext):
        """
        Process a restored timer. If the exec_time is still in the future, just
        calculate the new exec time and enqueue as usual. Otherwise, we have to
        enforce the TimerRecoveryPolicy in affect.
        """
        time_now = TimeUtc.now()
        if context.exec_time < time_now:
            # execution time is in the past ... enforce recoveryPolicy
            if self.recovery_policy == TimerRecoveryPolicy.RECOVER_FAIL:
                self.signal_error(context, TimerErrorCode.TIMER_ERROR_FAIL_IID, f'Recovered timer expired - IID {context.iid} will be terminated')
            elif self.recovery_policy == TimerRecoveryPolicy.RECOVER_FIRE:
                # fire the event immediately
                context.exec_time = time_now
                timer = WrappedTimer(self, 0, self.__timer_done_action, self.__timer_action, context)
                timer.start()
            elif self.recovery_policy == TimerRecoveryPolicy.RECOVER_FORGET:
                # mark the timer as lost
                logging.info(f'Dropped timer {context.guid}')
                if context.token_pool_id is not None:
                    tp = TokenPool.from_pool_name(context.token_pool_id)
                    tp.release_as_lost()
            # else: # self.recovery_policy == TimerRecoveryPolicy.RECOVER_FUTURE:
            #     # reschedule using NOW as base time
            #     pass
        else:
            duration = context.exec_time - time_now
            timer = WrappedTimer(self, duration, self.__timer_done_action, self.__timer_action, context)
            timer.start()

    def __timer_action(self, context:TimerContext, *args):
        """
        Called when a timer fires. This calls the callback provided when the
        timer was enqueued.

        Note that the callback is expected to handle any problems with communicating
        with other services, POST's, GET's, whatever so we just make the call here.
        """
        logging.info(f'{context.guid} __timer_action - calling back with {args}')
        resp = self.callback(*args)
        logging.info(f'{context.guid} Timer callback returned {resp}')
        return resp

    def __timer_done_action(self, context:TimerContext, abort:bool = False):
        """
        Called after a timer has fired. In this implementation, this could be
        combined with __timer_action, but keep it separate to give us more
        flexibility should we want separate done actions evoked for different
        scenarios.

        If we're not running a cycle timer, then we're done. If we are running
        a cycle timer and there are no more recurrences then we're done.
        Otherwise, calculate the maturity time for the next cycle and enqueue
        that timer.
        """

        # Document here all the various scenarios and write the logic to fit.

        # if there is an end date then last event must fire at that time.time
        # - calculate the time of the last event, and see if the next regular
        #   interval occurs before that.
        #   - if so, fire the interval event
        #   - otherwise fire the last event and complete the timer
        if abort:
            logging.info(f'{context.guid} timer aborted')
            self.completed = True
        elif context.continues:
            time_now   = TimeUtc.now()
            context.exec_time += context.interval
            if context.end_date is not None and context.end_date < context.exec_time:
                context.exec_time = context.end_date
            duration = context.exec_time - time_now
            if duration < 0:
                # TODO: enforce the recurrence recovery policy
                logging.info(f'{context.guid} Timer occurs in the past - firing immediately')
                duration = 0
            timer = WrappedTimer(self, duration, self.__timer_done_action, self.__timer_action, context)
            timer.start()
            context.decrement()
        else:
            logging.info(f'{context.guid} timer exhausted any/all recurrences')
            TimerContext.erase(context.key)
            self.completed = True

def test_callback(token_stack:str, data:str, iid:str, did:str, content_type:str) -> bool:
    print(f'Fired! {Functions.func_now()} {token_stack} {data} {iid} {did} {content_type}')
    return True # return False to test abort

def test_err_callback(iid:str, code:TimerErrorCode, message:str):
    print(f'Error! {Functions.func_now()} {iid} {code.name} {message}')

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    get_etcd()

    mgr = TimedEventManager('test_did', '["timeDate","{NOW()}"]', test_callback, test_err_callback, 'recover_fire', False)

    restored_json = '{"guid": "15338b7c88e642bbab48793a42bad81f", "iid":"test_did-test_did_iid", "timer_type": "TIME_DURATION", "start_date": 1625846154, "end_date": null, "interval": 300, "recurrence": 0, "spec": "PT5M", "token_stack": "", "exec_time": 1625846454, "token_pool_id": null, "args": ["{}", 1, "hello", "application/json"], "completed": false}'
    # ctx = TimerContext.from_json(restored_json)
    # ctx.save()
    # ctx0 = TimerContext.restore('test_did-test_did_iid')


    # mgr.restore_timer(ctx0)
    # spec = mgr._substitutor.do_sub({}, "{SUB(NOW(),PT1H)}")
    # print(spec)
    # results,_ = TimedEventManager.validate_spec('timeDate', spec)
    # print(results)
    # spec = mgr._substitutor.do_sub({}, "R3/{NOW()}/{ADD(NOW(),P5D)}")
    # results,_ = TimedEventManager.validate_spec('timeCycle', spec)
    # print(results)

    # results,_ = TimedEventManager.validate_spec('timeCycle', "R3/2021-01-01T12:00:00Z/2021-01-02T12:00:00Z")
    # print(results)
    # results,_ = TimedEventManager.validate_spec('timeCycle', "R/2021-01-01T12:00:00Z/2021-01-02T12:00:00Z")
    # print(results)
    # spec = '["timeCycle","R3/PT15S"]'
    # spec = '["timeCycle", "R/{NOW()}/{ADD(NOW(),PT3M)}"]' #RDD - unbounded for three minutes
    # spec = '["timeCycle", "R/PT3M/{ADD(NOW(),PT3M)}"]' #RPD - unbounded for three minutes
    # spec = '["timeCycle", "R/{NOW()}/PT1M"]' #RDP = unbounded for one minute
    # spec = '["timeCycle", "R4/{SUB(NOW(),PT2M)}/PT1M"]' #RDP = unbounded for one minute
    # spec = '["timeCycle", "R3/PT30S/{ADD(NOW(),PT4M)}"]' #RPD - three recurrences, three minutes apart, ending 20 minutes from now
    # spec = '["timeCycle", "R0/PT30S/{ADD(NOW(),PT3M)}"]' #RPD - three recurrences, three minutes apart, ending 20 minutes from now
    # spec = '["timeCycle", "R3/PT30S/{ADD(NOW(),PT1M)}"]' #RPD - three recurrences, three minutes apart, ending 20 minutes from now
    # mgr = TimedEventManager(spec, test_callback, False)
    # mgr.create_timer('test_iid', '',  [b'{}',1,'hello','application/json'])
    # time.sleep(10)
    # mgr.create_timer('test_iid', '',  [b'[]',2,'world','application/json'])
    # time.sleep(7)
    # mgr.create_timer('test_iid', '',  [b'[]',3,'people','application/json'])
    # mgr.enqueue(test_callback, '', 'test_flow_id','test_wf_id', 'application/json')

    #mgr = TimedEventManager('["timeDuration","P10D"]')
    # type = 'timeCycle'
    # spec = "R{repeat_cnt}/ADD({date}T12:00:00Z,PT{hour_cnt}H)/PT30M"
    # spec = "R{repeat_cnt}/ADD(NOW,PT30S)/PT{hour_cnt}S"
    # spec = "R{cycle_count}/ADD(NOW,PT{delay_secs}S)/PT{recur_delay}S"

    # mgr = TimedEventManager(f'["{type}","{spec}"]', test_callback)
    # locals = '{"date":"12-02-2020", "repeat_cnt":"3", "hour_cnt":"5"}'
    # term = TimedEventManager._json_substitution(locals, 'R{repeat_cnt}/ADD({date}T12:00:00Z,PT{hour_cnt}H)/PT30M')
    # term = TimedEventManager._json_substitution(locals, 'R{repeat_cnt}/DATE_ADD({date}T12:00:00Z,PT{hour_cnt}H)/{date}T23:59:59Z')
    # TimedEventManager._do_date_math(term)

    # R3/DATE_ADD(2021-01-01T12:0000,-PT2H)/kdlsjfa
    # def create_timer(self, wf_inst_id : str, token_stack : str, args : list):
    # args is [data, flow_id, wf_id, content_type]
    # mgr.create_timer('test_flow_id', None, [locals.encode('utf-8'), 'test_flow_id', 'test_wf_id', 'application/json'])

    # locals = '{"date-2020":"2020-12-01T00:00:00Z", "date-2021":"2021-12-01T00:00:00Z", "year":"2021", "repeat_cnt":"5", "hour_cnt":"7"}'
    # locals = '{"cycle_count":"3", "delay_secs":"30", "recur_delay":"45"}'
    # mgr.create_timer('test_flow_id', None, [locals.encode('utf-8'), 'test_flow_id', 'test_wf_id', 'application/json'])

    # x = TimedEvent(None, "timeDate", "2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeDuration", "P10D", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/PT10H", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/PT10H/2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/2011-03-11T12:13:14Z/PT10H", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/2011-03-11T12:13:14Z/PT10H/2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "2011-03-11T12:13:14Z/PT10H", "aKey", "aValue")

    # tests for timeCycle combinations
    # test_specs = [
    #     "R/PT10M",
    #     "R0/PT10M",
    #     "R3/PT10M",
    #     "R3/2021-01-01T12:00:00Z/P10D",
    #     "R3/P10D/2021-01-01T12:00:00Z",
    #     "R3/2021-01-01T12:00:00Z/2021-01-02T12:00:00Z",
    # ]

    # for spec in test_specs:
    #     results,_ = TimedEventManager.validate_spec('timeCycle', spec)
    #     print(results)

    # test for recovery
    # 1. Create a duration timer of 1H in the past
    # mgr = TimedEventManager('["timeDuration", "PT5M"]', test_callback, False)
    # mgr.create_timer('test_iid', '',  [b'{}',1,'hello','application/json'])
    # restored_json = '{"guid": "15338b7c88e642bbab48793a42bad81f", "timer_type": "TIME_DURATION", "start_date": 1625846154, "end_date": null, "interval": 300, "recurrence": 0, "spec": "PT5M", "token_stack": "", "exec_time": 1625846454, "token_pool_id": null, "args": ["{}", 1, "hello", "application/json"], "completed": false}'
    # ctx = TimerContext.from_json(restored_json)
    # mgr.restore_timer(ctx)

    # ctx = TimerContext(mgr.aspects, None, ['test_flow_id','test_wf_id', 'application/json'])
    # j = ctx.to_json()
    # print(j)
    # ctx1 = TimerContext.from_json(j)
    # print(ctx1)

