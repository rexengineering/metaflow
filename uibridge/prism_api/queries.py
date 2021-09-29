"""Query/Mutation definitions for GraphQL"""

TASK_START_MUTATION = '''
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

WORKFLOW_COMPLETE_MUTATION = '''
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