from flowlib import flow_pb2_grpc

from .handlers import handler_dispatch


class Flow(flow_pb2_grpc.FlowDaemon):

    def ApplyWorkflow(self, request, context):
        return handler_dispatch('apply', request, context)

    def DeleteWorkflow(self, request, context):
        return handler_dispatch('delete', request, context)

    def PSQuery(self, request, context):
        return handler_dispatch('ps', request, context)

    def RunWorkflow(self, request, context):
        return handler_dispatch('run', request, context)

    def StartWorkflow(self, request, context):
        return handler_dispatch('start', request, context)

    def StopWorkflow(self, request, context):
        return handler_dispatch('stop', request, context)

    def SetStatus(self, request, context):
        return handler_dispatch('setstatus', request, context)
