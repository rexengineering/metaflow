# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import flow_pb2 as flow__pb2


class FlowDaemonStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ApplyWorkflow = channel.unary_unary(
                '/FlowDaemon/ApplyWorkflow',
                request_serializer=flow__pb2.ApplyRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )
        self.DeleteWorkflow = channel.unary_unary(
                '/FlowDaemon/DeleteWorkflow',
                request_serializer=flow__pb2.DeleteRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )
        self.PSQuery = channel.unary_unary(
                '/FlowDaemon/PSQuery',
                request_serializer=flow__pb2.PSRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )
        self.RunWorkflow = channel.unary_unary(
                '/FlowDaemon/RunWorkflow',
                request_serializer=flow__pb2.RunRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )
        self.StartWorkflow = channel.unary_unary(
                '/FlowDaemon/StartWorkflow',
                request_serializer=flow__pb2.StartRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )
        self.StopWorkflow = channel.unary_unary(
                '/FlowDaemon/StopWorkflow',
                request_serializer=flow__pb2.StopRequest.SerializeToString,
                response_deserializer=flow__pb2.FlowdResult.FromString,
                )


class FlowDaemonServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ApplyWorkflow(self, request, context):
        """flowctl apply
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeleteWorkflow(self, request, context):
        """flowctl delete
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PSQuery(self, request, context):
        """flowctl ps
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RunWorkflow(self, request, context):
        """flowctl run
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StartWorkflow(self, request, context):
        """flowctl start
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StopWorkflow(self, request, context):
        """flowctl stop
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_FlowDaemonServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ApplyWorkflow': grpc.unary_unary_rpc_method_handler(
                    servicer.ApplyWorkflow,
                    request_deserializer=flow__pb2.ApplyRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
            'DeleteWorkflow': grpc.unary_unary_rpc_method_handler(
                    servicer.DeleteWorkflow,
                    request_deserializer=flow__pb2.DeleteRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
            'PSQuery': grpc.unary_unary_rpc_method_handler(
                    servicer.PSQuery,
                    request_deserializer=flow__pb2.PSRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
            'RunWorkflow': grpc.unary_unary_rpc_method_handler(
                    servicer.RunWorkflow,
                    request_deserializer=flow__pb2.RunRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
            'StartWorkflow': grpc.unary_unary_rpc_method_handler(
                    servicer.StartWorkflow,
                    request_deserializer=flow__pb2.StartRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
            'StopWorkflow': grpc.unary_unary_rpc_method_handler(
                    servicer.StopWorkflow,
                    request_deserializer=flow__pb2.StopRequest.FromString,
                    response_serializer=flow__pb2.FlowdResult.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'FlowDaemon', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class FlowDaemon(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ApplyWorkflow(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/ApplyWorkflow',
            flow__pb2.ApplyRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def DeleteWorkflow(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/DeleteWorkflow',
            flow__pb2.DeleteRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def PSQuery(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/PSQuery',
            flow__pb2.PSRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def RunWorkflow(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/RunWorkflow',
            flow__pb2.RunRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def StartWorkflow(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/StartWorkflow',
            flow__pb2.StartRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def StopWorkflow(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/FlowDaemon/StopWorkflow',
            flow__pb2.StopRequest.SerializeToString,
            flow__pb2.FlowdResult.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)
