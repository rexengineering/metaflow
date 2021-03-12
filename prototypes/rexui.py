import logging

from quart import request
import json

from flowlib.etcd_utils import get_etcd, transition_state
from flowlib.quart_app import QuartApp


class AsyncService(QuartApp):
    def __init__(self, **kws):
        super().__init__(__name__, **kws)
        self.etcd = get_etcd()
        self.app.route('/', methods=('POST',))(self.root_route)
    
    def root_route(self):
        ok = self.validate_request(request)
        if not ok:
            return Error("invalid input")
        else:
            executor.submit(self.handle_request(request))
        return "ok"

    def handle_request(self, request):
        # callback is URI of next task in workflow, for example, "Profit!"
        callback = self.get_callback(request)
        result = self.actual_handler(request)
        callback(result)


class REXFlowUIBridge(AsyncService):
    def __init__(self, **kws):
        super.__init__(**kws)
        self.app.route('/ui', methods=('POST',))(self.ui_route)
        self.app.route('/init', methods=['POST'])(self.init_route)

    def init_route(self):
        # When the WF Instance is created, we want the <instance_path>/userTasks/<user_task_id> to be set to PENDING (or something like that)
        wf_instance = request.headers['x-flow-id']
        user_task_id = self.config.this_user_task_id
        etcd.replace(f'/rexflow/instances/{wf_instance}/userTasks/{user_task_id}', 'pending', 'initialized')

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
    
    def get_callback(self, request):
        '''Can return one of the 4 verbs: Forms/save/validate/complete
        '''
        pass

    def actual_handler(self, request):
        
