# resolvers for mutations defined here
# Note: query resolvers are in resolvers.py
from ariadne import ObjectType

# instantiate the mutation objects here. If you add another one,
# you need to add it to the initializer list in app.py
mutation = ObjectType("Mutation")
session_mutation = ObjectType("SessionMutations")
session_state_mutations = ObjectType("StateMutations")

@mutation.field('session')
def mutation_session_mutations(_,info):
    return session_mutation

@session_mutation.field('start')
def session_mutation_start(_,info):
    print('session_mutation_start')
    return {'status':'SUCCESS'}

@session_mutation.field('state')
def session_mutation_status(_,info):
    print ('session_mutation_status')
    return session_state_mutations

@session_state_mutations.field('update')
def session_state_mutation_update(_,info,input):
    print(f'session_state_mutation_update {input}')
    return {'status':'SUCCESS'}

