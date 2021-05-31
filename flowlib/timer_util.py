'''
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


'''
import copy
import isodate
import json
import logging
import threading
import time
import typing

from datetime import datetime, timezone
from flowlib import token_api

class WrappedTimer:
    '''
    Python timers are created, start, and die without any notifications. This
    class wraps a threading.Timer object so that we can receive a notification
    once the timer matures.
    '''
    def __init__(self, interval : int, done_action : typing.Callable[[object],None], action : typing.Callable[[list],None], context : typing.Any):
        self._interval = interval
        self._done_action = done_action
        self._action = action
        self._context = context
        self._timer = threading.Timer(interval, self.do_action, context.values)
        logging.info(f'{time.time()} Timer created with duration {interval}')

    def do_action(self, *args):
        token_stack = self._context.token_stack
        if self._context.token_pool_id is not None:
            # need to pass the token_pool_id as an x header
            token_stack = self._context.token_pool_id if token_stack is None else f'{token_stack},{self._context.token_pool_id}'
            token_api.token_alloc(self._context.token_pool_id)

        self._action(token_stack,*args)

        self.done()

    def start(self):
        self._timer.start()
        logging.info(f'{time.time()} Starting timer')

    def cancel(self):
        self._timer.cancel()
        self.done()

    def done(self):
        logging.info(f'{time.time()} Timer done')
        self._done_action(self._context)

class TimedEventManager:
    SUBS_BEG = '{'
    SUBS_END = '}'
    FUNC_BEG = '('
    FUNC_END = ')'
    ADD_FUNC = 'ADD'
    SUB_FUNC = 'SUB'
    NOW      = 'NOW'
    DIVIDER  = '/'
    FUNCS = [ADD_FUNC,SUB_FUNC]
    ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    TIME_DATE      = 0
    TIME_DURATION  = 1
    TIME_CYCLE     = 2

    def __init__(self, timer_description_json : str, callback : typing.Callable[[list], None]):
        # TODO: load and schedule any persisted timed events
        self.events = dict()
        self.json = timer_description_json
        #[timer_type, timer_spec]
        self.timer_type, self.spec = json.loads(timer_description_json) 
        self.callback = callback
        # if validate_spec returns None, then the spec has dynamic references
        # i.e. {substitutions} and/or FUNCTIONS(), so we will resolve dynamically
        # in create_timer().
        self.aspects =  TimedEventManager.validate_spec(self.timer_type, self.spec.upper())
        self.is_dynamic_spec = self.aspects == None
        self.token_pool_id = None
        self.completed = True

    class ValidationResults:
        def __init__(self, timer_type : str, spec : str):
            self.timer_type_s = timer_type
            self.spec = spec
            self.start_date = None
            self.end_date = None
            self.interval = 0
            self.recurrance = 0

    def reset(self, aspects : ValidationResults) -> None:
        '''
        Reset the timer manager to the provided timer type and specification.
        This can only happen if the current configuration has already run its
        course.
        '''
        assert self.completed, 'Cannot reset - timer still active'
        self.aspects = aspects

    @classmethod
    def validate_spec(cls, timer_type : str, spec : str) -> ValidationResults:
        logging.info(f'Validating {timer_type} {spec}')
        # check here if spec contains any substitution or function markers. 
        # if so, return None
        if any( marker in [cls.FUNC_BEG, cls.SUBS_BEG] for marker in spec):
            logging.info('Deferring spec validation as spec has substitution/function markers')
            return None

        # the spec contains the ISO 8601 value apropos to type
        results = cls.ValidationResults(timer_type, spec)

        # all times must be in GMT (Zulu)
        # either a specific datetime or a duration must be specified
        # infinite recurrences are not allowed i.e. R/PT10H or R0/PT10H
        #
        # The number of seconds in 100 years is 3,155,695,200 seconds
        # which is way under the upper bound of an int in python 3, so
        # we're safe converting all fixed and relative times into
        # seconds.
        if timer_type == 'timeDate':
            # spec needs to be an ISO 8601 date/time to execute
            # e.g. 2011-03-11T12:13:14Z
            results.start_date = int(isodate.parse_datetime(spec).timestamp())
            results.timer_type = cls.TIME_DATE
            logging.info(f'timeDate timing event created - executing on {datetime.fromtimestamp(results.start_date)}')

        elif timer_type == 'timeDuration':
            # spec needs to be an ISO 8601 period
            # e.g. P10D
            assert spec.startswith('P'), 'Duration timed events must with P'
            results.interval = int(isodate.parse_duration(spec).total_seconds())
            results.timer_type = cls.TIME_DURATION
            logging.info(f'timeDuration timing event created - {results.interval} seconds')

        elif timer_type == 'timeCycle':
            # spec need to be an ISO 8601 Repeating Interval
            # e.g. R3/PT10H
            assert spec.startswith('R'), 'Cycle timed events must begin with R'
            assert '/' in spec, 'Cycle timed events must provide recurrence and duration'
            toks = cls.parse_spec(spec)
            pat = toks[0]
            # acceptable patterns are RP, RPD, RDP
            # RP - recurrence and interval
            # RPD - recurrence, interval, end date
            # RDP - recurrence, start date, and interval
            # RDPD - recurrance, start date, interval, end date
            assert pat in ['RP','RPD','RDP','RDPD'], 'Improper cycle definition'
            datum = toks[1]
            results.recurrance = datum[0]
            if pat == 'RP':
                results.interval = datum[1]
                logging.info(f'timeCycle timing event created - {results.recurrance} cycle(s) '
                             f'{results.interval} seconds apart')

            elif pat == 'RDP':
                results.start_date = datum[1]
                results.interval   = datum[2]
                logging.info(f'timeCycle timing event created - {results.recurrance} cycle(s) '
                             f'{results.interval} seconds apart '
                             f'starting on {datetime.fromtimestamp(results.start_date)}')

            elif pat == 'RPD':
                results.interval = datum[1]
                results.end_date = datum[2]
                logging.info(f'timeCycle timing event created - {results.recurrance} cycle(s) '
                             f'{results.interval} seconds apart '
                             f'ending no later than {datetime.fromtimestamp(results.end_date)}')

            else: # pat == 'RDPD'
                results.start_date = datum[1]
                results.interval   = datum[2]
                results.end_date   = datum[3]
                assert results.start_date <= results.end_date, "Error - start date must preceed end date"
                logging.info(f'timeCycle timing event created - {results.recurrance} cycle(s) '
                             f'{results.interval} seconds apart, '
                             f'starting on {datetime.fromtimestamp(results.start_date)} '
                             f'and ending no later than {datetime.fromtimestamp(results.end_date)}')

            results.timer_type = cls.TIME_CYCLE
        else:
            raise ValueError(f'Illegal timed event type specified: {timer_type}')
        return results

    @classmethod
    def parse_spec(cls, spec : str) -> list:
        '''
        Parse the time period specification as per ISO 8601-1
        - elements are separated by '/' (4.4.2.a)
        - element that start with 'P' is a PERIOD (4.4.2.b)
        - element that starts with 'R' is a RECURRANCE (4.5.2)
        - otherwise the element is parsed as a DATETIME (4.3)

        Return a tuple of a pattern of encountered data elements, e.g.
        'RP' for a recurrence/period, and a list of result objects,
        e.g. ['RP',[3,103420]]
        '''
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
                val = int(elem[1::]) if len(elem) > 1 else 0
            else:
                # DATETIME
                cat += 'D'
                val = int(isodate.parse_datetime(elem).timestamp())
            results.append(val)

        return [cat,results]

    def create_timer(self, wf_inst_id : str, token_stack : str, args : list):
        '''
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
        '''

        # if self.is_dynamic_spec is True, then we need to validate the spec employing
        # information passed in with the request
        if self.is_dynamic_spec:
            # args[0] is the data provided with the incoming request. This should be
            # JSON. So, decode that, and pass it to the substiution logic to get a
            # "current" timer specification, then validate that. Oy.
            req_json     = json.loads(args[0].decode())
            adj_spec     = self._json_substitution(req_json, self.spec)
            self.aspects = self.validate_spec(self.timer_type, adj_spec)

        context = TimerContext(self, token_stack, args)

        time_now = int(time.time())
        if context.start_date is None:
            context.start_date = time_now
        elif context.start_date < time_now:
            logging.info(f'Specified launch time has passed - event will fire immediatly')
            context.start_date = time_now
        if context.end_date is not None:
            exec_time = time_now + self.aspects.interval
            assert exec_time <= context.end_date, "Execution terminated - execution time exceeds specified end time."
        if self.aspects.timer_type == self.TIME_CYCLE:
            # cycle types need a token pool for remote collectors/end events to keep track of the number
            # of recurrences seen.
            context.token_pool_id = token_api.token_create_pool(wf_inst_id, self.aspects.recurrance)
            logging.info(f'Created token pool {context.token_pool_id}')

        self.completed = False
        duration = context.start_date - time_now + self.aspects.interval
        timer = WrappedTimer(duration, self.timer_done_action, self.timer_action, context)
        timer.start()

        if self.aspects.timer_type == self.TIME_CYCLE:
            context.recurrance = context.recurrance - 1

    def timer_action(self, *data):
        '''
        Called when a timer fires. This calls the callback provided when the
        timer was enqueued.

        Note that the callback is expected to handle any problems with communicating
        with other services, POST's, GET's, whatever so we just make the call here.
        '''
        logging.info(f'timer_action - calling back with {data}')
        try:
            resp = self.callback(*data)
            logging.info(f'Timer callback returned {resp}')
        except Exception as ex:
            logging.exception('Callback threw exception, which was ignored', exc_info=ex)

    def timer_done_action(self, context):
        '''
        Called after a timer has fired. In this implementation, this could be
        combined with timer_action, but keep it separate to give us more
        flexibility should we want separate done actions evoked for different
        scenarios.

        If we're not running a cycle timer, then we're done. If we are running
        a cycle timer and there are no more recurrences then we're done.
        Otherwise, calculate the maturity time for the next cycle and enqueue
        that timer.
        '''
        if self.aspects.timer_type == self.TIME_CYCLE and context.recurrance > 0:
            if context.end_date is not None:
                exec_time = int(time.time()) + self.aspects.interval
                assert exec_time <= context.end_date, "Recursion terminated - execution time exceeds specified end time."
            timer = WrappedTimer(self.aspects.interval, self.timer_done_action, self.timer_action, context)
            timer.start()
            context.recurrance = context.recurrance - 1
        else:
            self.completed = True

    @classmethod
    def _json_substitution(cls, locals:dict, src:str) -> str:
        '''
        Take an input string with (supposed) embedded token references bracketed by {}
        e.g. "hello {world}" In this case, the token "world" is abstracted, and a node
        with that name is searched in the json.
        '''
        itr = enumerate(src)
        trg = cls._sub_json_token(locals, itr, 0, '')
        logging.info(f'Json sub results {src}\n{trg}')
        return trg

    @classmethod
    def _sub_json_token(cls, locals:dict, itr:enumerate, level:int, bank:str, func:str = None) -> str:

        trg = ''
        for _,c in itr: 
            if c == cls.SUBS_BEG:
                # found a nested reference - so resolve it
                trg += cls._sub_json_token(locals, itr, level + 1, bank)
            elif c == cls.SUBS_END:
                if (level):
                    # trg contains a JSON path to be resolved, and its
                    # value used in place of the identified path
                    return locals[trg]
                # otherwise error?
            elif c == cls.FUNC_BEG:
                # trg contains the name of a function
                trg = trg.upper()
                if not trg in cls.FUNCS:
                    raise ValueError(f'Unknown function: {trg}')
                trg = cls._sub_json_token(locals, itr, level + 1, bank, trg)
            elif c == cls.FUNC_END:
                # trg contains parms to the function
                return cls._proc_func(func,trg)
            else:
                trg += c
                if c == cls.DIVIDER:
                    # bank trg and start over - but keep the separator
                    bank += trg
                    trg = ''
        # if (level) error?
        return bank + trg

    @classmethod
    def _proc_func(cls, func:str, parms:str):
        res  = ''
        args = []
        for arg in parms.split(','):
            if arg == cls.NOW:
                val = datetime.now(timezone.utc).timestamp()
            else:
                val = cls.parse_spec(arg)[1][0]
            args.append(val)

        if func == cls.ADD_FUNC:
            args[0] += args[1]
            res = datetime.fromtimestamp(args[0]).strftime(cls.ISO_8601_FORMAT)
        elif func == cls.SUB_FUNC:
            args[0] -= args[1]
            res = datetime.fromtimestamp(args[0]).strftime(cls.ISO_8601_FORMAT)
        else:
            raise NameError(f'Unknown function {func}')
        return res

class TimerContext:
    def __init__(self, source : TimedEventManager, token_stack : str, vals : list):
        self.timer_type    = source.aspects.timer_type
        self.start_date    = source.aspects.start_date
        self.end_date      = source.aspects.end_date
        self.interval      = source.aspects.interval
        self.recurrance    = source.aspects.recurrance
        self.token_stack   = token_stack
        self.token_pool_id = None
        self.values        = vals
        self.completed     = False

def test_callback(token_stack : str, data : str, flow_id : str, wf_id : str, content_type : str):
    print(f'Fired! {token_stack} {data} {flow_id} {wf_id} {content_type}')

if __name__ == "__main__":
    # mgr = TimedEventManager('["timeDate","2011-03-11T12:13:14Z"]')
    # mgr.enqueue(test_callback, '', 'test_flow_id','test_wf_id', 'application/json')

    #mgr = TimedEventManager('["timeDuration","P10D"]')
    type = 'timeCycle'
    # spec = "R{repeat_cnt}/ADD({date}T12:00:00Z,PT{hour_cnt}H)/PT30M"
    # spec = "R{repeat_cnt}/ADD(NOW,PT30S)/PT{hour_cnt}S"
    spec = "R{repeat_cnt}/ADD({date-{year}},PT30S)/PT{hour_cnt}S"

    mgr = TimedEventManager(f'["{type}","{spec}"]', test_callback)
    # locals = '{"date":"12-02-2020", "repeat_cnt":"3", "hour_cnt":"5"}'
    # term = TimedEventManager._json_substitution(locals, 'R{repeat_cnt}/ADD({date}T12:00:00Z,PT{hour_cnt}H)/PT30M')
    # term = TimedEventManager._json_substitution(locals, 'R{repeat_cnt}/DATE_ADD({date}T12:00:00Z,PT{hour_cnt}H)/{date}T23:59:59Z')
    # TimedEventManager._do_date_math(term)

    # R3/DATE_ADD(2021-01-01T12:0000,-PT2H)/kdlsjfa
    # def create_timer(self, wf_inst_id : str, token_stack : str, args : list):
    # args is [data, flow_id, wf_id, content_type]
    # mgr.create_timer('test_flow_id', None, [locals.encode('utf-8'), 'test_flow_id', 'test_wf_id', 'application/json'])

    locals = '{"date-2020":"2020-12-01T00:00:00Z", "date-2021":"2021-12-01T00:00:00Z", "year":"2021", "repeat_cnt":"5", "hour_cnt":"7"}'
    mgr.create_timer('test_flow_id', None, [locals.encode('utf-8'), 'test_flow_id', 'test_wf_id', 'application/json'])

    # x = TimedEvent(None, "timeDate", "2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeDuration", "P10D", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/PT10H", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/PT10H/2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/2011-03-11T12:13:14Z/PT10H", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "R3/2011-03-11T12:13:14Z/PT10H/2011-03-11T12:13:14Z", "aKey", "aValue")
    # x = TimedEvent(None, "timeCycle", "2011-03-11T12:13:14Z/PT10H", "aKey", "aValue")
