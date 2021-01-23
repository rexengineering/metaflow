'''
These are the valid states for a workflow and the workflow instances, specified here
so that all parts necessarily use the same values and to avoid embedding literal
constants everywhere.
'''


class States:
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    RUNNING = 'RUNNING'
    START = 'START'
    STARTING = 'STARTING'
    STOPPED = 'STOPPED'
    STOPPING = 'STOPPING'
    TRUE = 'TRUE'


# TODO: research caching this conversion.
class ByteStatesClass:
    def __getattr__(self, name):
        return getattr(States, name).encode('utf-8')


BStates = ByteStatesClass()

REXFLOW_ROOT = '/rexflow'
TRACEID_HEADER = 'X-B3-Traceid'


class WorkflowKeys:
    ROOT = f'{REXFLOW_ROOT}/workflows'

    def __init__(self, id):
        self.root = self.key_of(id)
        self.proc = self.proc_key(id)
        self.probe = self.probe_key(id)
        self.state = self.state_key(id)

    @classmethod
    def key_of(cls, id):
        return f'{WorkflowKeys.ROOT}/{id}'

    @classmethod
    def proc_key(cls, id):
        return f'{cls.key_of(id)}/proc'

    @classmethod
    def probe_key(cls, id):
        return f'{cls.key_of(id)}/probes'

    @classmethod
    def task_key(cls, wf_id, task_id):
        return f'{cls.probe_key(wf_id)}/{task_id}'

    @classmethod
    def state_key(cls, id):
        return f'{cls.key_of(id)}/state'


class WorkflowInstanceKeys:
    ROOT = f'{REXFLOW_ROOT}/instances'

    def __init__(self, id):
        self.root = self.key_of(id)
        self.proc = self.proc_key(id)
        self.result = self.result_key(id)
        self.state = self.state_key(id)
        self.headers = self.headers_key(id)
        self.payload = self.payload_key(id)
        self.error_key = self.was_error_key(id)
        self.parent = self.parent_key(id)
        self.end_event = self.end_event_key(id)
        self.traceid = self.traceid_key(id)
        self.content_type = self.content_type_key(id)

    @classmethod
    def key_of(cls, id):
        return f'{WorkflowInstanceKeys.ROOT}/{id}'

    @classmethod
    def proc_key(cls, id):
        return f'{cls.key_of(id)}/proc'

    @classmethod
    def state_key(cls, id):
        return f'{cls.key_of(id)}/state'

    @classmethod
    def result_key(cls, id):
        return f'{cls.key_of(id)}/result'

    @classmethod
    def payload_key(cls, id):
        return f'{cls.key_of(id)}/payload'

    @classmethod
    def headers_key(cls, id):
        return f'{cls.key_of(id)}/headers'

    @classmethod
    def was_error_key(cls, id):
        return f'{cls.key_of(id)}/wasError'

    @classmethod
    def parent_key(cls, id):
        return f'{cls.key_of(id)}/parent'

    @classmethod
    def end_event_key(cls, id):
        return f'{cls.key_of(id)}/end_event'

    @classmethod
    def traceid_key(cls, id):
        return f'{cls.key_of(id)}/traceid'

    @classmethod
    def content_type_key(cls, id):
        return f'{cls.key_of(id)}/content_type'


def split_key(instance_id: str):
    '''
    Accept a key in the form of <workflow_id>-<guid>
    and return a tuple of (workflow_id,guid)

    It's assumed that the instance_id has no occurance of '-'
    othwerise this breaks.
    '''
    parts = instance_id.split('-')
    return ('-'.join(parts[0:-1]), '-'.join(parts[-1]))


def flow_result(status: int, message: str, **kwargs):
    result = {'status': status, 'message': message}
    result.update(kwargs)
    return result
