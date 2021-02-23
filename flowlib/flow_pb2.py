# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: flow.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='flow.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\nflow.proto\"<\n\x0b\x46lowdResult\x12\x0e\n\x06status\x18\x01 \x01(\x03\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\t\"1\n\x0c\x41pplyRequest\x12\x10\n\x08\x62pmn_xml\x18\x01 \x01(\t\x12\x0f\n\x07stopped\x18\x02 \x01(\x08\"8\n\rDeleteRequest\x12\x1a\n\x04kind\x18\x01 \x01(\x0e\x32\x0c.RequestKind\x12\x0b\n\x03ids\x18\x02 \x03(\t\"4\n\tPSRequest\x12\x1a\n\x04kind\x18\x01 \x01(\x0e\x32\x0c.RequestKind\x12\x0b\n\x03ids\x18\x02 \x03(\t\"\x1b\n\x0cProbeRequest\x12\x0b\n\x03ids\x18\x01 \x03(\t\"@\n\nRunRequest\x12\x13\n\x0bworkflow_id\x18\x01 \x01(\t\x12\x0c\n\x04\x61rgs\x18\x02 \x03(\t\x12\x0f\n\x07stopped\x18\x03 \x01(\x08\"7\n\x0cStartRequest\x12\x1a\n\x04kind\x18\x01 \x01(\x0e\x32\x0c.RequestKind\x12\x0b\n\x03ids\x18\x02 \x03(\t\"6\n\x0bStopRequest\x12\x1a\n\x04kind\x18\x01 \x01(\x0e\x32\x0c.RequestKind\x12\x0b\n\x03ids\x18\x02 \x03(\t*+\n\x0bRequestKind\x12\x0e\n\nDEPLOYMENT\x10\x00\x12\x0c\n\x08INSTANCE\x10\x01\x32\xc1\x02\n\nFlowDaemon\x12,\n\rApplyWorkflow\x12\r.ApplyRequest\x1a\x0c.FlowdResult\x12.\n\x0e\x44\x65leteWorkflow\x12\x0e.DeleteRequest\x1a\x0c.FlowdResult\x12#\n\x07PSQuery\x12\n.PSRequest\x1a\x0c.FlowdResult\x12,\n\rProbeWorkflow\x12\r.ProbeRequest\x1a\x0c.FlowdResult\x12(\n\x0bRunWorkflow\x12\x0b.RunRequest\x1a\x0c.FlowdResult\x12,\n\rStartWorkflow\x12\r.StartRequest\x1a\x0c.FlowdResult\x12*\n\x0cStopWorkflow\x12\x0c.StopRequest\x1a\x0c.FlowdResultb\x06proto3'
)

_REQUESTKIND = _descriptor.EnumDescriptor(
  name='RequestKind',
  full_name='RequestKind',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DEPLOYMENT', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='INSTANCE', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=447,
  serialized_end=490,
)
_sym_db.RegisterEnumDescriptor(_REQUESTKIND)

RequestKind = enum_type_wrapper.EnumTypeWrapper(_REQUESTKIND)
DEPLOYMENT = 0
INSTANCE = 1



_FLOWDRESULT = _descriptor.Descriptor(
  name='FlowdResult',
  full_name='FlowdResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='FlowdResult.status', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='message', full_name='FlowdResult.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data', full_name='FlowdResult.data', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=14,
  serialized_end=74,
)


_APPLYREQUEST = _descriptor.Descriptor(
  name='ApplyRequest',
  full_name='ApplyRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='bpmn_xml', full_name='ApplyRequest.bpmn_xml', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='stopped', full_name='ApplyRequest.stopped', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=76,
  serialized_end=125,
)


_DELETEREQUEST = _descriptor.Descriptor(
  name='DeleteRequest',
  full_name='DeleteRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='kind', full_name='DeleteRequest.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ids', full_name='DeleteRequest.ids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=127,
  serialized_end=183,
)


_PSREQUEST = _descriptor.Descriptor(
  name='PSRequest',
  full_name='PSRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='kind', full_name='PSRequest.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ids', full_name='PSRequest.ids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=185,
  serialized_end=237,
)


_PROBEREQUEST = _descriptor.Descriptor(
  name='ProbeRequest',
  full_name='ProbeRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ids', full_name='ProbeRequest.ids', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=239,
  serialized_end=266,
)


_RUNREQUEST = _descriptor.Descriptor(
  name='RunRequest',
  full_name='RunRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='workflow_id', full_name='RunRequest.workflow_id', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='args', full_name='RunRequest.args', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='stopped', full_name='RunRequest.stopped', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=268,
  serialized_end=332,
)


_STARTREQUEST = _descriptor.Descriptor(
  name='StartRequest',
  full_name='StartRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='kind', full_name='StartRequest.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ids', full_name='StartRequest.ids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=334,
  serialized_end=389,
)


_STOPREQUEST = _descriptor.Descriptor(
  name='StopRequest',
  full_name='StopRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='kind', full_name='StopRequest.kind', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ids', full_name='StopRequest.ids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=391,
  serialized_end=445,
)

_DELETEREQUEST.fields_by_name['kind'].enum_type = _REQUESTKIND
_PSREQUEST.fields_by_name['kind'].enum_type = _REQUESTKIND
_STARTREQUEST.fields_by_name['kind'].enum_type = _REQUESTKIND
_STOPREQUEST.fields_by_name['kind'].enum_type = _REQUESTKIND
DESCRIPTOR.message_types_by_name['FlowdResult'] = _FLOWDRESULT
DESCRIPTOR.message_types_by_name['ApplyRequest'] = _APPLYREQUEST
DESCRIPTOR.message_types_by_name['DeleteRequest'] = _DELETEREQUEST
DESCRIPTOR.message_types_by_name['PSRequest'] = _PSREQUEST
DESCRIPTOR.message_types_by_name['ProbeRequest'] = _PROBEREQUEST
DESCRIPTOR.message_types_by_name['RunRequest'] = _RUNREQUEST
DESCRIPTOR.message_types_by_name['StartRequest'] = _STARTREQUEST
DESCRIPTOR.message_types_by_name['StopRequest'] = _STOPREQUEST
DESCRIPTOR.enum_types_by_name['RequestKind'] = _REQUESTKIND
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

FlowdResult = _reflection.GeneratedProtocolMessageType('FlowdResult', (_message.Message,), {
  'DESCRIPTOR' : _FLOWDRESULT,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:FlowdResult)
  })
_sym_db.RegisterMessage(FlowdResult)

ApplyRequest = _reflection.GeneratedProtocolMessageType('ApplyRequest', (_message.Message,), {
  'DESCRIPTOR' : _APPLYREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:ApplyRequest)
  })
_sym_db.RegisterMessage(ApplyRequest)

DeleteRequest = _reflection.GeneratedProtocolMessageType('DeleteRequest', (_message.Message,), {
  'DESCRIPTOR' : _DELETEREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:DeleteRequest)
  })
_sym_db.RegisterMessage(DeleteRequest)

PSRequest = _reflection.GeneratedProtocolMessageType('PSRequest', (_message.Message,), {
  'DESCRIPTOR' : _PSREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:PSRequest)
  })
_sym_db.RegisterMessage(PSRequest)

ProbeRequest = _reflection.GeneratedProtocolMessageType('ProbeRequest', (_message.Message,), {
  'DESCRIPTOR' : _PROBEREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:ProbeRequest)
  })
_sym_db.RegisterMessage(ProbeRequest)

RunRequest = _reflection.GeneratedProtocolMessageType('RunRequest', (_message.Message,), {
  'DESCRIPTOR' : _RUNREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:RunRequest)
  })
_sym_db.RegisterMessage(RunRequest)

StartRequest = _reflection.GeneratedProtocolMessageType('StartRequest', (_message.Message,), {
  'DESCRIPTOR' : _STARTREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:StartRequest)
  })
_sym_db.RegisterMessage(StartRequest)

StopRequest = _reflection.GeneratedProtocolMessageType('StopRequest', (_message.Message,), {
  'DESCRIPTOR' : _STOPREQUEST,
  '__module__' : 'flow_pb2'
  # @@protoc_insertion_point(class_scope:StopRequest)
  })
_sym_db.RegisterMessage(StopRequest)



_FLOWDAEMON = _descriptor.ServiceDescriptor(
  name='FlowDaemon',
  full_name='FlowDaemon',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=493,
  serialized_end=814,
  methods=[
  _descriptor.MethodDescriptor(
    name='ApplyWorkflow',
    full_name='FlowDaemon.ApplyWorkflow',
    index=0,
    containing_service=None,
    input_type=_APPLYREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='DeleteWorkflow',
    full_name='FlowDaemon.DeleteWorkflow',
    index=1,
    containing_service=None,
    input_type=_DELETEREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='PSQuery',
    full_name='FlowDaemon.PSQuery',
    index=2,
    containing_service=None,
    input_type=_PSREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='ProbeWorkflow',
    full_name='FlowDaemon.ProbeWorkflow',
    index=3,
    containing_service=None,
    input_type=_PROBEREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='RunWorkflow',
    full_name='FlowDaemon.RunWorkflow',
    index=4,
    containing_service=None,
    input_type=_RUNREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='StartWorkflow',
    full_name='FlowDaemon.StartWorkflow',
    index=5,
    containing_service=None,
    input_type=_STARTREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='StopWorkflow',
    full_name='FlowDaemon.StopWorkflow',
    index=6,
    containing_service=None,
    input_type=_STOPREQUEST,
    output_type=_FLOWDRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_FLOWDAEMON)

DESCRIPTOR.services_by_name['FlowDaemon'] = _FLOWDAEMON

# @@protoc_insertion_point(module_scope)
