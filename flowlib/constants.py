'''
These are the valid states for a workflow and the workflow instances, specified here
so that all parts necessarilly use the same values and to avoid embedding literal
constants everywhere.
'''
class States:
    COMPLETED = 'COMPLETED'
    ERROR     = 'ERROR'
    RUNNING   = 'RUNNING'
    START     = 'START'
    STARTING  = 'STARTING'
    STOPPED   = 'STOPPED'
    STOPPING  = 'STOPPING'

# TODO: research caching this conversion.
class ByteStatesClass:
    def __getattr__(self, name):
        return getattr(States,name).encode('utf-8')

BStates = ByteStatesClass()

REXFLOW_ROOT = '/rexflow'

class WorkflowKeys:
    ROOT = f'{REXFLOW_ROOT}/workflows'

    def __init__(self, id):
        self.root  = self.key_of(id)
        self.proc  = self.proc_key(id)
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
        self.root   = self.key_of(id)
        self.proc   = self.proc_key(id)
        self.result = self.result_key(id)
        self.state  = self.state_key(id)

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

'''
Accept a key in the form of <workflow_id>-<guid>
and return a tuple of (workflow_id,guid)

It's assumed that the instance_id has no occurance of '-'
othwerise this breaks.
'''
def split_key(instance_id : str):
    parts = instance_id.split('-');
    return ('-'.join(parts[0:-1]), '-'.join(parts[-1]))

