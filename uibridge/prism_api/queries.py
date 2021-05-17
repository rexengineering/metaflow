'''Query/Mutation definitions for GraphQL'''

START_TASK_MUTATION = '''
mutation StartTask($startTaskInput: StartTaskInput!) {
  task {
    start(input: $startTaskInput) {
      status
      errors { 
        message
      }
    }
  }
}
'''

COMPLETE_WORKFLOW_MUTATION = '''
mutation CompleteWorkflow($completeWorkflowInput: CompleteWorkflowInput!) {
  workflow {
    complete(input: $completeWorkflowInput) {
      status
      errors {
        message
      }
    }
  }
}
'''