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


