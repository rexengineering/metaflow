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

# TODO: Move these to the Headers namespace.
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

HOST_SUFFIX = '/host'
REXFLOW_ROOT = REXFLOW_ROOT_PREFIX


class Headers:
    '''Because namespace pollution affects us all...
    '''
    FLOWID_HEADER = 'X-Flow-Id'
    TRACEID_HEADER = 'X-B3-Traceid'
    WFID_HEADER = 'X-Rexflow-Wf-Id'


class WorkflowKeys:
    ROOT = f'{REXFLOW_ROOT}/workflows'

    def __init__(self, did):
        self.root = self.key_of(did)
        self.proc = self.proc_key(did)
        self.probe = self.probe_key(did)
        self.state = self.state_key(did)
        self.host = self.host_key(did)

        # Actually an S3 key since we don't store the k8s specs in etcd.
        self.specs = self.specs_key(did)

    @classmethod
    def key_of(cls, did):
        return f'{WorkflowKeys.ROOT}/{did}'

    @classmethod
    def proc_key(cls, did):
        return f'{cls.key_of(did)}/proc'

    @classmethod
    def probe_key(cls, did):
        return f'{cls.key_of(did)}/probes'

    @classmethod
    def task_key(cls, did, tid):
        return f'{cls.probe_key(did)}/{tid}'

    @classmethod
    def state_key(cls, did):
        return f'{cls.key_of(did)}/state'

    @classmethod
    def specs_key(cls, did):
        return f'{cls.key_of(did)}/k8s_specs'

    @classmethod
    def host_key(cls, did):
        return f'{cls.key_of(did)}{HOST_SUFFIX}'

    @classmethod
    def field_key(cls,did,tid):
        return f'{cls.key_of(did)}/fields/{tid}'


# TODO: There seems to be a proliferation of instance-related keys in ETCD.
# Schedule a careful review of these and remove as many as possible.

class WorkflowInstanceKeys:
    ROOT = f'{REXFLOW_ROOT}/instances'

    def __init__(self, iid):
        self.root           = self.key_of(iid)
        self.proc           = self.proc_key(iid)
        self.result         = self.result_key(iid)
        self.state          = self.state_key(iid)
        self.error_code     = self.error_code_key(iid)
        self.error_message  = self.error_message_key(iid)
        self.failed_task    = self.failed_task_key(iid)
        self.input_headers  = self.input_headers_key(iid)
        self.input_data     = self.input_data_key(iid)
        self.output_data    = self.output_data_key(iid)
        self.output_headers = self.output_headers_key(iid)
        self.parent         = self.parent_key(iid)
        self.end_event      = self.end_event_key(iid)
        self.traceid        = self.traceid_key(iid)
        self.content_type   = self.content_type_key(iid)
        self.timed_events   = self.timed_events_key(iid)
        self.timed_results  = self.timed_results_key(iid)

    @classmethod
    def key_of(cls, iid):
        return f'{WorkflowInstanceKeys.ROOT}/{iid}'

    @classmethod
    def proc_key(cls, iid):
        return f'{cls.key_of(iid)}/proc'

    @classmethod
    def state_key(cls, iid):
        return f'{cls.key_of(iid)}/state'

    @classmethod
    def result_key(cls, iid):
        return f'{cls.key_of(iid)}/result'

    @classmethod
    def payload_key(cls, iid):
        return f'{cls.key_of(iid)}/payload'

    @classmethod
    def headers_key(cls, iid):
        return f'{cls.key_of(iid)}/headers'

    @classmethod
    def parent_key(cls, iid):
        return f'{cls.key_of(iid)}/parent'

    @classmethod
    def end_event_key(cls, iid):
        return f'{cls.key_of(iid)}/end_event'

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
    def traceid_key(cls, iid):
        return f'{cls.key_of(iid)}/traceid'

    @classmethod
    def content_type_key(cls, iid):
        return f'{cls.key_of(iid)}/content_type'

    @classmethod
    def timed_events_key(cls, iid):
        return f'{cls.key_of(iid)}/timed_events'

    @classmethod
    def timed_results_key(cls, iid):
        return f'{cls.key_of(iid)}/timed_results'

    @classmethod
    def form_key(cls, iid):
        return f'{cls.key_of(iid)}/forms'

    @classmethod
    def task_form_key(cls, iid, tid):
        return f'{cls.form_key(iid)}/{tid}'

    @classmethod
    def ui_server_uri_key(cls, iid):
        return f'{cls.form_key(iid)}/graphql_uri'

def split_key(iid: str):
    '''
    Accept a key in the form of <workflow_id>-<guid>
    and return a tuple of (workflow_id,guid)

    It's assumed that the instance_id has no occurance of '-'
    othwerise this breaks.
    '''
    parts = iid.split('-')
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
