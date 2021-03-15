from quart import request

from flowlib.constants import flow_result
from .async_service import AsyncService


class REXFlowUIBridge(AsyncService):
    def __init__(self, **kws):
        super.__init__(**kws)
        self.app.route('/ui', methods=['POST'])(self.ui_route)
        self.app.route('/init', methods=['POST'])(self.init_route)

    def init_route(self):
        # When the WF Instance is created, we want the <instance_path>/userTasks/<user_task_id> to be set to PENDING (or something like that)
        wf_instance = request.headers['x-flow-id']
        user_task_id = self.config.this_user_task_id
        self.etcd.replace(f'/rexflow/instances/{wf_instance}/userTasks/{user_task_id}', 'pending', 'initialized')

    def ui_route(self):
        state = self.get_state_from_etcd(request)  # Gets ID from request...
        command = self.get_command_from_request(request)

        # TODO: allow for more flexible state transitions, including multiple SAVE's
        # or potentially a CANCEL.
        if (state, command) == ('initialized', 'forms'):
            return self.get_forms(request)
        elif (state, command) == ('forms_sent', 'save'):
            return self.save_forms(request)
        elif (state, command) == ('forms_saved', 'validate'):
            return self.validate_forms(request)
        elif (state, command) == ('validated', 'complete'):
            return self.completed(request)
        return self.handle_error(request)

    def get_state_from_etcd(self, request):
        raise NotImplementedError('Lazy developer error!')

    def get_command_from_request(self, request):
        raise NotImplementedError('Lazy developer error!')

    def get_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def save_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def validate_forms(self, request):
        raise NotImplementedError('Lazy developer error!')

    def completed(self, request):
        raise NotImplementedError('Lazy developer error!')

    def handle_error(self, request):
        return flow_result(-1, 'Error: Invalid command!')

    def get_callback(self, request):
        '''Can return one of the 4 verbs: Forms/save/validate/complete
        '''
        pass

    def actual_handler(self, request):
        # FIXME: Pass REXFlow environment from request in the result.
        return flow_result(0, 'Ok')
