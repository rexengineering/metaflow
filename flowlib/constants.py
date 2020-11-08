# These are the valid states for a workflow and the workflow instances, specified here
# so that all parts necessarilly use the same values and to avoid embedding literal
# constants everywhere.
#

class States:
    COMPLETED = b'COMPLETED'
    ERROR     = b'ERROR'
    RUNNING   = b'RUNNING'
    START     = b'START'
    STARTING  = b'STARTING'
    STOPPED   = b'STOPPED'
    STOPPING  = b'STOPPING'
