from hashlib import sha256
import re
from flowlib.config import REXFLOW_ROOT_PREFIX

'''
These are the valid states for a workflow and the workflow instances, specified here
so that all parts necessarily use the same values and to avoid embedding literal
constants everywhere.
'''

BPMN_INTERMEDIATE_CATCH_EVENT = 'bpmn:intermediateCatchEvent'
BPMN_START_EVENT = 'bpmn:startEvent'
BPMN_TIMER_EVENT_DEFINITION = 'bpmn:timerEventDefinition'

TIMER_DESCRIPTION = 'TIMER_DESCRIPTION'

X_HEADER_FLOW_ID = 'X-Flow-Id'
X_HEADER_WORKFLOW_ID = 'X-Rexflow-Wf-Id'
X_HEADER_TOKEN_POOL_ID = 'X-Rexflow-Token-Pool-Id'
X_HEADER_TASK_ID = 'X-Rexflow-Task-Id'

K8S_MAX_NAMELENGTH = 63


def to_valid_k8s_name(name):
    '''
    Takes in a name and massages it until it complies to the k8s name regex, which is:
        [a-z0-9]([-a-z0-9]*[a-z0-9])?
    Raises an AssertionError if we fail to make the name comply.
    '''
    name = name.lower()

    # Replace space-like chars with a '-'
    name = re.sub('[. _\n]', '-', name)

    # Remove invalid characters
    name = re.sub('[^0-9a-z-]', '', name)

    # Remove repeated dashes
    name = re.sub('-[-]+', '-', name)

    # Trim leading and trailing dashes
    name = name.rstrip('-').lstrip('-')

    # K8s names limited to 63 or fewer characters. We could truncate to 63, but doing so could
    # lead to conflicts if the caller of this function was relying on some UID at the end of
    # the name. Therefore, we add another hash.
    if len(name) > K8S_MAX_NAMELENGTH:
        token = f'-{sha256(name.encode()).hexdigest()[:8]}'
        name = name[:(K8S_MAX_NAMELENGTH - len(token))] + token

    assert len(name) > 0, "Must provide at least one valid character [a-b0-9A-B]."
    assert re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', name), \
        f"NewGradProgrammerError: Was unable to make name {name} k8s-compatible."
    assert len(name) <= 63, "NewGradProgrammerError: k8s names must be <63 char long."
    return name


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

REXFLOW_ROOT = REXFLOW_ROOT_PREFIX
TRACEID_HEADER = 'X-B3-Traceid'


class WorkflowKeys:
    ROOT = f'{REXFLOW_ROOT}/workflows'

    def __init__(self, id):
        self.root = self.key_of(id)
        self.proc = self.proc_key(id)
        self.probe = self.probe_key(id)
        self.state = self.state_key(id)

        # Actually an S3 key since we don't store the k8s specs in etcd.
        self.specs = self.specs_key(id)

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

    @classmethod
    def specs_key(cls, id):
        return f'{cls.key_of(id)}/k8s_specs'


class WorkflowInstanceKeys:
    ROOT = f'{REXFLOW_ROOT}/instances'

    def __init__(self, id):
        self.root           = self.key_of(id)
        self.proc           = self.proc_key(id)
        self.result         = self.result_key(id)
        self.state          = self.state_key(id)
        self.error_code     = self.error_code_key(id)
        self.error_message  = self.error_message_key(id)
        self.failed_task    = self.failed_task_key(id)
        self.input_headers  = self.input_headers_key(id)
        self.input_data     = self.input_data_key(id)
        self.output_data    = self.output_data_key(id)
        self.output_headers = self.output_headers_key(id)
        self.parent         = self.parent_key(id)
        self.end_event      = self.end_event_key(id)
        self.traceid        = self.traceid_key(id)
        self.content_type   = self.content_type_key(id)
        self.timed_events   = self.timed_events_key(id)
        self.timed_results  = self.timed_results_key(id)

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
    def error_code_key(cls, id):
        return f'{cls.key_of(id)}/error_code'

    @classmethod
    def failed_task_key(cls, id):
        return f'{cls.key_of(id)}/failed_task'

    @classmethod
    def error_message_key(cls, id):
        return f'{cls.key_of(id)}/error_message'

    @classmethod
    def input_headers_key(cls, id):
        return f'{cls.key_of(id)}/input_headers'

    @classmethod
    def input_data_key(cls, id):
        return f'{cls.key_of(id)}/input_data'

    @classmethod
    def output_headers_key(cls, id):
        return f'{cls.key_of(id)}/output_headers'

    @classmethod
    def output_data_key(cls, id):
        return f'{cls.key_of(id)}/output_data'

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
        
    @classmethod
    def timed_events_key(cls, id):
        return f'{cls.key_of(id)}/timed_events'

    @classmethod
    def timed_results_key(cls, id):
        return f'{cls.key_of(id)}/timed_results'

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


def get_ingress_object_name(hostname):
    long_name = f'rexflow-{hostname}-{sha256(hostname.encode()).hexdigest()[:8]}'
    return to_valid_k8s_name(long_name)


class IngressHostKeys:
    ROOT = f'{REXFLOW_ROOT}/hosts'

    def __init__(self, host):
        self.workflow_id = self.workflow_id_key(host)
        self.component_name = self.component_name_key(host)

    @classmethod
    def key_of(cls, host):
        return f'{IngressHostKeys.ROOT}/{host}'

    @classmethod
    def workflow_id_key(cls, host):
        return f'{cls.key_of(host)}/workflow_id'

    @classmethod
    def component_name_key(cls, host):
        return f'{cls.key_of(host)}/component_name'
