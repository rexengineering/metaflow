'''Utility library for working with BPMN documents.
'''


def get_tasks(process):
    '''Given a BPMN process, get the service tasks in that process.
    Arguments:
        process - OrderedDict instance containing a BPMN process.
    Returns:
        List of OrderedDict instances for each service task.
    '''
    tasks = process.get('bpmn:serviceTask')
    if tasks is None:
       return []
    elif not isinstance(tasks, list):
        return [tasks]
    return tasks
