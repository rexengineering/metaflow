from ariadne import ScalarType, ObjectType

session_id = ScalarType('SessionId')
workflow_id = ScalarType('WorkflowInstance')
workflow_type = ObjectType('Workflow')
task_id = ScalarType('TaskId')
state = ScalarType('State')
