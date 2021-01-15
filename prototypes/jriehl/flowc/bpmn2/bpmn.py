'''Automatically generated from a Moddle JSON representation'''

from typing import List, Union

from .. import cmof

class ProcessType(cmof.Enum):
    None_='None'
    Public='Public'
    Private='Private'
ProcessType._ns={'prefix': 'bpmn', 'localName': 'ProcessType', 'name': 'bpmn:ProcessType'}

class GatewayDirection(cmof.Enum):
    Unspecified='Unspecified'
    Converging='Converging'
    Diverging='Diverging'
    Mixed='Mixed'
GatewayDirection._ns={'prefix': 'bpmn', 'localName': 'GatewayDirection', 'name': 'bpmn:GatewayDirection'}

class EventBasedGatewayType(cmof.Enum):
    Parallel='Parallel'
    Exclusive='Exclusive'
EventBasedGatewayType._ns={'prefix': 'bpmn', 'localName': 'EventBasedGatewayType', 'name': 'bpmn:EventBasedGatewayType'}

class RelationshipDirection(cmof.Enum):
    None_='None'
    Forward='Forward'
    Backward='Backward'
    Both='Both'
RelationshipDirection._ns={'prefix': 'bpmn', 'localName': 'RelationshipDirection', 'name': 'bpmn:RelationshipDirection'}

class ItemKind(cmof.Enum):
    Physical='Physical'
    Information='Information'
ItemKind._ns={'prefix': 'bpmn', 'localName': 'ItemKind', 'name': 'bpmn:ItemKind'}

class ChoreographyLoopType(cmof.Enum):
    None_='None'
    Standard='Standard'
    MultiInstanceSequential='MultiInstanceSequential'
    MultiInstanceParallel='MultiInstanceParallel'
ChoreographyLoopType._ns={'prefix': 'bpmn', 'localName': 'ChoreographyLoopType', 'name': 'bpmn:ChoreographyLoopType'}

class AssociationDirection(cmof.Enum):
    None_='None'
    One='One'
    Both='Both'
AssociationDirection._ns={'prefix': 'bpmn', 'localName': 'AssociationDirection', 'name': 'bpmn:AssociationDirection'}

class MultiInstanceBehavior(cmof.Enum):
    None_='None'
    One='One'
    All='All'
    Complex='Complex'
MultiInstanceBehavior._ns={'prefix': 'bpmn', 'localName': 'MultiInstanceBehavior', 'name': 'bpmn:MultiInstanceBehavior'}

class AdHocOrdering(cmof.Enum):
    Parallel='Parallel'
    Sequential='Sequential'
AdHocOrdering._ns={'prefix': 'bpmn', 'localName': 'AdHocOrdering', 'name': 'bpmn:AdHocOrdering'}

class BaseElement(cmof.Element):
    id: cmof.String
    _contents: Union['ExtensionElements', List['Documentation'], List[cmof.Ref['ExtensionDefinition']]]
    _ns={'prefix': 'bpmn', 'localName': 'BaseElement', 'name': 'bpmn:BaseElement'}

class Extension(cmof.Element):
    definition: 'ExtensionDefinition'
    mustUnderstand: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'Extension', 'name': 'bpmn:Extension'}

class ExtensionAttributeDefinition(cmof.Element):
    extensionDefinition: 'ExtensionDefinition'
    isReference: cmof.Boolean
    name: cmof.String
    type: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'ExtensionAttributeDefinition', 'name': 'bpmn:ExtensionAttributeDefinition'}

class ExtensionDefinition(cmof.Element):
    name: cmof.String
    _contents: List[ExtensionAttributeDefinition]
    _ns={'prefix': 'bpmn', 'localName': 'ExtensionDefinition', 'name': 'bpmn:ExtensionDefinition'}

class ExtensionElements(cmof.Element):
    extensionAttributeDefinition: ExtensionAttributeDefinition
    valueRef: cmof.Element
    _contents: List[cmof.Element]
    _ns={'prefix': 'bpmn', 'localName': 'ExtensionElements', 'name': 'bpmn:ExtensionElements'}

class Import(cmof.Element):
    importType: cmof.String
    location: cmof.String
    namespace: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Import', 'name': 'bpmn:Import'}

class InputOutputBinding(cmof.Element):
    inputDataRef: 'InputSet'
    operationRef: 'Operation'
    outputDataRef: 'OutputSet'
    _ns={'prefix': 'bpmn', 'localName': 'InputOutputBinding', 'name': 'bpmn:InputOutputBinding'}

class InteractionNode(cmof.Element):
    _contents: List[cmof.Ref['ConversationLink']]
    _ns={'prefix': 'bpmn', 'localName': 'InteractionNode', 'name': 'bpmn:InteractionNode'}

class Artifact(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'Artifact', 'name': 'bpmn:Artifact'}

class Assignment(BaseElement):
    _contents: 'Expression'
    _ns={'prefix': 'bpmn', 'localName': 'Assignment', 'name': 'bpmn:Assignment'}

class Auditing(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'Auditing', 'name': 'bpmn:Auditing'}

class CategoryValue(BaseElement):
    value: cmof.String
    _contents: List[cmof.Ref['FlowElement']]
    _ns={'prefix': 'bpmn', 'localName': 'CategoryValue', 'name': 'bpmn:CategoryValue'}

class ComplexBehaviorDefinition(BaseElement):
    _contents: Union['FormalExpression', 'ImplicitThrowEvent']
    _ns={'prefix': 'bpmn', 'localName': 'ComplexBehaviorDefinition', 'name': 'bpmn:ComplexBehaviorDefinition'}

class ConversationAssociation(BaseElement):
    innerConversationNodeRef: 'ConversationNode'
    outerConversationNodeRef: 'ConversationNode'
    _ns={'prefix': 'bpmn', 'localName': 'ConversationAssociation', 'name': 'bpmn:ConversationAssociation'}

class ConversationLink(BaseElement):
    name: cmof.String
    sourceRef: InteractionNode
    targetRef: InteractionNode
    _ns={'prefix': 'bpmn', 'localName': 'ConversationLink', 'name': 'bpmn:ConversationLink'}

class ConversationNode(InteractionNode, BaseElement):
    name: cmof.String
    _contents: Union[List['CorrelationKey'], List[cmof.Ref['MessageFlow']], List[cmof.Ref['Participant']]]
    _ns={'prefix': 'bpmn', 'localName': 'ConversationNode', 'name': 'bpmn:ConversationNode'}

class CorrelationKey(BaseElement):
    name: cmof.String
    _contents: List[cmof.Ref['CorrelationProperty']]
    _ns={'prefix': 'bpmn', 'localName': 'CorrelationKey', 'name': 'bpmn:CorrelationKey'}

class CorrelationPropertyBinding(BaseElement):
    correlationPropertyRef: 'CorrelationProperty'
    _contents: 'FormalExpression'
    _ns={'prefix': 'bpmn', 'localName': 'CorrelationPropertyBinding', 'name': 'bpmn:CorrelationPropertyBinding'}

class CorrelationPropertyRetrievalExpression(BaseElement):
    messageRef: 'Message'
    _contents: 'FormalExpression'
    _ns={'prefix': 'bpmn', 'localName': 'CorrelationPropertyRetrievalExpression', 'name': 'bpmn:CorrelationPropertyRetrievalExpression'}

class CorrelationSubscription(BaseElement):
    correlationKeyRef: CorrelationKey
    _contents: List[CorrelationPropertyBinding]
    _ns={'prefix': 'bpmn', 'localName': 'CorrelationSubscription', 'name': 'bpmn:CorrelationSubscription'}

class DataAssociation(BaseElement):
    _contents: Union['FormalExpression', List[Assignment], List[cmof.Ref['ItemAwareElement']], cmof.Ref['ItemAwareElement']]
    _ns={'prefix': 'bpmn', 'localName': 'DataAssociation', 'name': 'bpmn:DataAssociation'}

class DataState(BaseElement):
    name: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'DataState', 'name': 'bpmn:DataState'}

class Definitions(BaseElement):
    exporter: cmof.String
    exporterVersion: cmof.String
    expressionLanguage: cmof.String
    name: cmof.String
    targetNamespace: cmof.String
    typeLanguage: cmof.String
    _contents: Union[List['Relationship'], List['RootElement'], List['bpmndi.BPMNDiagram'], List[Extension], List[Import]]
    _ns={'prefix': 'bpmn', 'localName': 'Definitions', 'name': 'bpmn:Definitions'}

class Documentation(BaseElement):
    textFormat: cmof.String
    _contents: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Documentation', 'name': 'bpmn:Documentation'}

class Expression(BaseElement):
    _contents: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Expression', 'name': 'bpmn:Expression'}

class FlowElement(BaseElement):
    name: cmof.String
    _contents: Union['Monitoring', Auditing, List[cmof.Ref[CategoryValue]]]
    _ns={'prefix': 'bpmn', 'localName': 'FlowElement', 'name': 'bpmn:FlowElement'}

class FlowElementsContainer(BaseElement):
    _contents: Union[List['LaneSet'], List[FlowElement]]
    _ns={'prefix': 'bpmn', 'localName': 'FlowElementsContainer', 'name': 'bpmn:FlowElementsContainer'}

class InputOutputSpecification(BaseElement):
    _contents: Union[List['DataInput'], List['DataOutput'], List['InputSet'], List['OutputSet']]
    _ns={'prefix': 'bpmn', 'localName': 'InputOutputSpecification', 'name': 'bpmn:InputOutputSpecification'}

class InputSet(BaseElement):
    name: cmof.String
    _contents: Union[List[cmof.Ref['DataInput']], List[cmof.Ref['OutputSet']]]
    _ns={'prefix': 'bpmn', 'localName': 'InputSet', 'name': 'bpmn:InputSet'}

class ItemAwareElement(BaseElement):
    itemSubjectRef: 'ItemDefinition'
    _contents: DataState
    _ns={'prefix': 'bpmn', 'localName': 'ItemAwareElement', 'name': 'bpmn:ItemAwareElement'}

class Lane(BaseElement):
    name: cmof.String
    partitionElementRef: BaseElement
    _contents: Union['LaneSet', BaseElement, List[cmof.Ref['FlowNode']]]
    _ns={'prefix': 'bpmn', 'localName': 'Lane', 'name': 'bpmn:Lane'}

class LaneSet(BaseElement):
    name: cmof.String
    _contents: List[Lane]
    _ns={'prefix': 'bpmn', 'localName': 'LaneSet', 'name': 'bpmn:LaneSet'}

class LoopCharacteristics(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'LoopCharacteristics', 'name': 'bpmn:LoopCharacteristics'}

class MessageFlow(BaseElement):
    messageRef: 'Message'
    name: cmof.String
    sourceRef: InteractionNode
    targetRef: InteractionNode
    _ns={'prefix': 'bpmn', 'localName': 'MessageFlow', 'name': 'bpmn:MessageFlow'}

class MessageFlowAssociation(BaseElement):
    innerMessageFlowRef: MessageFlow
    outerMessageFlowRef: MessageFlow
    _ns={'prefix': 'bpmn', 'localName': 'MessageFlowAssociation', 'name': 'bpmn:MessageFlowAssociation'}

class Monitoring(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'Monitoring', 'name': 'bpmn:Monitoring'}

class Operation(BaseElement):
    implementationRef: cmof.String
    name: cmof.String
    _contents: Union[List[cmof.Ref['Error']], cmof.Ref['Message']]
    _ns={'prefix': 'bpmn', 'localName': 'Operation', 'name': 'bpmn:Operation'}

class OutputSet(BaseElement):
    name: cmof.String
    _contents: Union[List[cmof.Ref['DataOutput']], List[cmof.Ref[InputSet]]]
    _ns={'prefix': 'bpmn', 'localName': 'OutputSet', 'name': 'bpmn:OutputSet'}

class Participant(InteractionNode, BaseElement):
    name: cmof.String
    processRef: 'Process'
    _contents: Union['ParticipantMultiplicity', List[cmof.Ref['EndPoint']], List[cmof.Ref['Interface']]]
    _ns={'prefix': 'bpmn', 'localName': 'Participant', 'name': 'bpmn:Participant'}

class ParticipantAssociation(BaseElement):
    innerParticipantRef: Participant
    outerParticipantRef: Participant
    _ns={'prefix': 'bpmn', 'localName': 'ParticipantAssociation', 'name': 'bpmn:ParticipantAssociation'}

class ParticipantMultiplicity(BaseElement):
    maximum: cmof.Integer
    minimum: cmof.Integer
    _ns={'prefix': 'bpmn', 'localName': 'ParticipantMultiplicity', 'name': 'bpmn:ParticipantMultiplicity'}

class Relationship(BaseElement):
    direction: RelationshipDirection
    type: cmof.String
    _contents: List[cmof.Ref[cmof.Element]]
    _ns={'prefix': 'bpmn', 'localName': 'Relationship', 'name': 'bpmn:Relationship'}

class Rendering(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'Rendering', 'name': 'bpmn:Rendering'}

class ResourceAssignmentExpression(BaseElement):
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'ResourceAssignmentExpression', 'name': 'bpmn:ResourceAssignmentExpression'}

class ResourceParameter(BaseElement):
    isRequired: cmof.Boolean
    name: cmof.String
    type: 'ItemDefinition'
    _ns={'prefix': 'bpmn', 'localName': 'ResourceParameter', 'name': 'bpmn:ResourceParameter'}

class ResourceParameterBinding(BaseElement):
    parameterRef: ResourceParameter
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'ResourceParameterBinding', 'name': 'bpmn:ResourceParameterBinding'}

class ResourceRole(BaseElement):
    name: cmof.String
    _contents: Union[List[ResourceParameterBinding], ResourceAssignmentExpression, cmof.Ref['Resource']]
    _ns={'prefix': 'bpmn', 'localName': 'ResourceRole', 'name': 'bpmn:ResourceRole'}

class RootElement(BaseElement):
    _ns={'prefix': 'bpmn', 'localName': 'RootElement', 'name': 'bpmn:RootElement'}

class Association(Artifact):
    associationDirection: AssociationDirection
    sourceRef: BaseElement
    targetRef: BaseElement
    _ns={'prefix': 'bpmn', 'localName': 'Association', 'name': 'bpmn:Association'}

class CallConversation(ConversationNode):
    calledCollaborationRef: 'Collaboration'
    _contents: List[ParticipantAssociation]
    _ns={'prefix': 'bpmn', 'localName': 'CallConversation', 'name': 'bpmn:CallConversation'}

class CallableElement(RootElement):
    name: cmof.String
    _contents: Union[InputOutputSpecification, List[InputOutputBinding], List[cmof.Ref['Interface']]]
    _ns={'prefix': 'bpmn', 'localName': 'CallableElement', 'name': 'bpmn:CallableElement'}

class Category(RootElement):
    name: cmof.String
    _contents: List[CategoryValue]
    _ns={'prefix': 'bpmn', 'localName': 'Category', 'name': 'bpmn:Category'}

class Collaboration(RootElement):
    isClosed: cmof.Boolean
    name: cmof.String
    _contents: Union[ConversationAssociation, List[Artifact], List[ConversationLink], List[ConversationNode], List[CorrelationKey], List[MessageFlowAssociation], List[MessageFlow], List[ParticipantAssociation], List[Participant], List[cmof.Ref['Choreography']]]
    _ns={'prefix': 'bpmn', 'localName': 'Collaboration', 'name': 'bpmn:Collaboration'}

class Conversation(ConversationNode):
    _ns={'prefix': 'bpmn', 'localName': 'Conversation', 'name': 'bpmn:Conversation'}

class CorrelationProperty(RootElement):
    name: cmof.String
    type: 'ItemDefinition'
    _contents: List[CorrelationPropertyRetrievalExpression]
    _ns={'prefix': 'bpmn', 'localName': 'CorrelationProperty', 'name': 'bpmn:CorrelationProperty'}

class DataInput(ItemAwareElement):
    isCollection: cmof.Boolean
    name: cmof.String
    _contents: List[cmof.Ref[InputSet]]
    _ns={'prefix': 'bpmn', 'localName': 'DataInput', 'name': 'bpmn:DataInput'}

class DataInputAssociation(DataAssociation):
    _ns={'prefix': 'bpmn', 'localName': 'DataInputAssociation', 'name': 'bpmn:DataInputAssociation'}

class DataObject(FlowElement, ItemAwareElement):
    isCollection: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'DataObject', 'name': 'bpmn:DataObject'}

class DataObjectReference(ItemAwareElement, FlowElement):
    dataObjectRef: DataObject
    _ns={'prefix': 'bpmn', 'localName': 'DataObjectReference', 'name': 'bpmn:DataObjectReference'}

class DataOutput(ItemAwareElement):
    isCollection: cmof.Boolean
    name: cmof.String
    _contents: List[cmof.Ref[OutputSet]]
    _ns={'prefix': 'bpmn', 'localName': 'DataOutput', 'name': 'bpmn:DataOutput'}

class DataOutputAssociation(DataAssociation):
    _ns={'prefix': 'bpmn', 'localName': 'DataOutputAssociation', 'name': 'bpmn:DataOutputAssociation'}

class DataStore(RootElement, ItemAwareElement):
    capacity: cmof.Integer
    isUnlimited: cmof.Boolean
    name: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'DataStore', 'name': 'bpmn:DataStore'}

class DataStoreReference(ItemAwareElement, FlowElement):
    dataStoreRef: DataStore
    _ns={'prefix': 'bpmn', 'localName': 'DataStoreReference', 'name': 'bpmn:DataStoreReference'}

class EndPoint(RootElement):
    _ns={'prefix': 'bpmn', 'localName': 'EndPoint', 'name': 'bpmn:EndPoint'}

class Error(RootElement):
    errorCode: cmof.String
    name: cmof.String
    structureRef: 'ItemDefinition'
    _ns={'prefix': 'bpmn', 'localName': 'Error', 'name': 'bpmn:Error'}

class Escalation(RootElement):
    escalationCode: cmof.String
    name: cmof.String
    structureRef: 'ItemDefinition'
    _ns={'prefix': 'bpmn', 'localName': 'Escalation', 'name': 'bpmn:Escalation'}

class EventDefinition(RootElement):
    _ns={'prefix': 'bpmn', 'localName': 'EventDefinition', 'name': 'bpmn:EventDefinition'}

class FlowNode(FlowElement):
    _contents: Union[List[cmof.Ref['SequenceFlow']], List[cmof.Ref[Lane]]]
    _ns={'prefix': 'bpmn', 'localName': 'FlowNode', 'name': 'bpmn:FlowNode'}

class FormalExpression(Expression):
    evaluatesToTypeRef: 'ItemDefinition'
    language: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'FormalExpression', 'name': 'bpmn:FormalExpression'}

class Group(Artifact):
    categoryValueRef: CategoryValue
    _ns={'prefix': 'bpmn', 'localName': 'Group', 'name': 'bpmn:Group'}

class Interface(RootElement):
    implementationRef: cmof.String
    name: cmof.String
    _contents: List[Operation]
    _ns={'prefix': 'bpmn', 'localName': 'Interface', 'name': 'bpmn:Interface'}

class ItemDefinition(RootElement):
    import_: Import
    isCollection: cmof.Boolean
    itemKind: ItemKind
    structureRef: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'ItemDefinition', 'name': 'bpmn:ItemDefinition'}

class Message(RootElement):
    itemRef: ItemDefinition
    name: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Message', 'name': 'bpmn:Message'}

class MultiInstanceLoopCharacteristics(LoopCharacteristics):
    behavior: MultiInstanceBehavior
    isSequential: cmof.Boolean
    noneBehaviorEventRef: EventDefinition
    oneBehaviorEventRef: EventDefinition
    _contents: Union[DataInput, DataOutput, Expression, List[ComplexBehaviorDefinition], cmof.Ref[ItemAwareElement]]
    _ns={'prefix': 'bpmn', 'localName': 'MultiInstanceLoopCharacteristics', 'name': 'bpmn:MultiInstanceLoopCharacteristics'}

class PartnerEntity(RootElement):
    name: cmof.String
    _contents: List[cmof.Ref[Participant]]
    _ns={'prefix': 'bpmn', 'localName': 'PartnerEntity', 'name': 'bpmn:PartnerEntity'}

class PartnerRole(RootElement):
    name: cmof.String
    _contents: List[cmof.Ref[Participant]]
    _ns={'prefix': 'bpmn', 'localName': 'PartnerRole', 'name': 'bpmn:PartnerRole'}

class Performer(ResourceRole):
    _ns={'prefix': 'bpmn', 'localName': 'Performer', 'name': 'bpmn:Performer'}

class Property(ItemAwareElement):
    name: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Property', 'name': 'bpmn:Property'}

class Resource(RootElement):
    name: cmof.String
    _contents: List[ResourceParameter]
    _ns={'prefix': 'bpmn', 'localName': 'Resource', 'name': 'bpmn:Resource'}

class SequenceFlow(FlowElement):
    isImmediate: cmof.Boolean
    sourceRef: FlowNode
    targetRef: FlowNode
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'SequenceFlow', 'name': 'bpmn:SequenceFlow'}

class Signal(RootElement):
    name: cmof.String
    structureRef: ItemDefinition
    _ns={'prefix': 'bpmn', 'localName': 'Signal', 'name': 'bpmn:Signal'}

class StandardLoopCharacteristics(LoopCharacteristics):
    loopMaximum: cmof.Integer
    testBefore: cmof.Boolean
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'StandardLoopCharacteristics', 'name': 'bpmn:StandardLoopCharacteristics'}

class SubConversation(ConversationNode):
    _contents: List[ConversationNode]
    _ns={'prefix': 'bpmn', 'localName': 'SubConversation', 'name': 'bpmn:SubConversation'}

class TextAnnotation(Artifact):
    textFormat: cmof.String
    _contents: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'TextAnnotation', 'name': 'bpmn:TextAnnotation'}

class Activity(FlowNode):
    completionQuantity: cmof.Integer
    default: SequenceFlow
    isForCompensation: cmof.Boolean
    startQuantity: cmof.Integer
    _contents: Union[InputOutputSpecification, List[DataInputAssociation], List[DataOutputAssociation], List[Property], List[ResourceRole], List[cmof.Ref['BoundaryEvent']], LoopCharacteristics]
    _ns={'prefix': 'bpmn', 'localName': 'Activity', 'name': 'bpmn:Activity'}

class CancelEventDefinition(EventDefinition):
    _ns={'prefix': 'bpmn', 'localName': 'CancelEventDefinition', 'name': 'bpmn:CancelEventDefinition'}

class Choreography(Collaboration, FlowElementsContainer):
    _ns={'prefix': 'bpmn', 'localName': 'Choreography', 'name': 'bpmn:Choreography'}

class ChoreographyActivity(FlowNode):
    initiatingParticipantRef: Participant
    loopType: ChoreographyLoopType
    _contents: Union[List[CorrelationKey], List[cmof.Ref[Participant]]]
    _ns={'prefix': 'bpmn', 'localName': 'ChoreographyActivity', 'name': 'bpmn:ChoreographyActivity'}

class CompensateEventDefinition(EventDefinition):
    activityRef: Activity
    waitForCompletion: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'CompensateEventDefinition', 'name': 'bpmn:CompensateEventDefinition'}

class ConditionalEventDefinition(EventDefinition):
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'ConditionalEventDefinition', 'name': 'bpmn:ConditionalEventDefinition'}

class ErrorEventDefinition(EventDefinition):
    errorRef: Error
    _ns={'prefix': 'bpmn', 'localName': 'ErrorEventDefinition', 'name': 'bpmn:ErrorEventDefinition'}

class EscalationEventDefinition(EventDefinition):
    escalationRef: Escalation
    _ns={'prefix': 'bpmn', 'localName': 'EscalationEventDefinition', 'name': 'bpmn:EscalationEventDefinition'}

class Event(FlowNode, InteractionNode):
    _contents: List[Property]
    _ns={'prefix': 'bpmn', 'localName': 'Event', 'name': 'bpmn:Event'}

class Gateway(FlowNode):
    gatewayDirection: GatewayDirection
    _ns={'prefix': 'bpmn', 'localName': 'Gateway', 'name': 'bpmn:Gateway'}

class GlobalConversation(Collaboration):
    _ns={'prefix': 'bpmn', 'localName': 'GlobalConversation', 'name': 'bpmn:GlobalConversation'}

class GlobalTask(CallableElement):
    _contents: List[ResourceRole]
    _ns={'prefix': 'bpmn', 'localName': 'GlobalTask', 'name': 'bpmn:GlobalTask'}

class HumanPerformer(Performer):
    _ns={'prefix': 'bpmn', 'localName': 'HumanPerformer', 'name': 'bpmn:HumanPerformer'}

class LinkEventDefinition(EventDefinition):
    name: cmof.String
    target: 'LinkEventDefinition'
    _contents: List[cmof.Ref['LinkEventDefinition']]
    _ns={'prefix': 'bpmn', 'localName': 'LinkEventDefinition', 'name': 'bpmn:LinkEventDefinition'}

class MessageEventDefinition(EventDefinition):
    messageRef: Message
    operationRef: Operation
    _ns={'prefix': 'bpmn', 'localName': 'MessageEventDefinition', 'name': 'bpmn:MessageEventDefinition'}

class Process(FlowElementsContainer, CallableElement):
    definitionalCollaborationRef: Collaboration
    isClosed: cmof.Boolean
    isExecutable: cmof.Boolean
    processType: ProcessType
    _contents: Union[Auditing, List[Artifact], List[CorrelationSubscription], List[FlowElement], List[LaneSet], List[Property], List[ResourceRole], List[cmof.Ref['Process']], Monitoring]
    _ns={'prefix': 'bpmn', 'localName': 'Process', 'name': 'bpmn:Process'}

class SignalEventDefinition(EventDefinition):
    signalRef: Signal
    _ns={'prefix': 'bpmn', 'localName': 'SignalEventDefinition', 'name': 'bpmn:SignalEventDefinition'}

class TerminateEventDefinition(EventDefinition):
    _ns={'prefix': 'bpmn', 'localName': 'TerminateEventDefinition', 'name': 'bpmn:TerminateEventDefinition'}

class TimerEventDefinition(EventDefinition):
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'TimerEventDefinition', 'name': 'bpmn:TimerEventDefinition'}

class CallActivity(Activity):
    calledElement: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'CallActivity', 'name': 'bpmn:CallActivity'}

class CallChoreography(ChoreographyActivity):
    calledChoreographyRef: Choreography
    _contents: List[ParticipantAssociation]
    _ns={'prefix': 'bpmn', 'localName': 'CallChoreography', 'name': 'bpmn:CallChoreography'}

class CatchEvent(Event):
    parallelMultiple: cmof.Boolean
    _contents: Union[List[DataOutputAssociation], List[DataOutput], List[EventDefinition], List[cmof.Ref[EventDefinition]], OutputSet]
    _ns={'prefix': 'bpmn', 'localName': 'CatchEvent', 'name': 'bpmn:CatchEvent'}

class ChoreographyTask(ChoreographyActivity):
    _contents: List[cmof.Ref[MessageFlow]]
    _ns={'prefix': 'bpmn', 'localName': 'ChoreographyTask', 'name': 'bpmn:ChoreographyTask'}

class ComplexGateway(Gateway):
    default: SequenceFlow
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'ComplexGateway', 'name': 'bpmn:ComplexGateway'}

class EventBasedGateway(Gateway):
    eventGatewayType: EventBasedGatewayType
    instantiate: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'EventBasedGateway', 'name': 'bpmn:EventBasedGateway'}

class ExclusiveGateway(Gateway):
    default: SequenceFlow
    _ns={'prefix': 'bpmn', 'localName': 'ExclusiveGateway', 'name': 'bpmn:ExclusiveGateway'}

class GlobalBusinessRuleTask(GlobalTask):
    implementation: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'GlobalBusinessRuleTask', 'name': 'bpmn:GlobalBusinessRuleTask'}

class GlobalChoreographyTask(Choreography):
    initiatingParticipantRef: Participant
    _ns={'prefix': 'bpmn', 'localName': 'GlobalChoreographyTask', 'name': 'bpmn:GlobalChoreographyTask'}

class GlobalManualTask(GlobalTask):
    _ns={'prefix': 'bpmn', 'localName': 'GlobalManualTask', 'name': 'bpmn:GlobalManualTask'}

class GlobalScriptTask(GlobalTask):
    script: cmof.String
    scriptLanguage: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'GlobalScriptTask', 'name': 'bpmn:GlobalScriptTask'}

class GlobalUserTask(GlobalTask):
    implementation: cmof.String
    _contents: List[Rendering]
    _ns={'prefix': 'bpmn', 'localName': 'GlobalUserTask', 'name': 'bpmn:GlobalUserTask'}

class InclusiveGateway(Gateway):
    default: SequenceFlow
    _ns={'prefix': 'bpmn', 'localName': 'InclusiveGateway', 'name': 'bpmn:InclusiveGateway'}

class ParallelGateway(Gateway):
    _ns={'prefix': 'bpmn', 'localName': 'ParallelGateway', 'name': 'bpmn:ParallelGateway'}

class PotentialOwner(HumanPerformer):
    _ns={'prefix': 'bpmn', 'localName': 'PotentialOwner', 'name': 'bpmn:PotentialOwner'}

class SubChoreography(ChoreographyActivity, FlowElementsContainer):
    _contents: List[Artifact]
    _ns={'prefix': 'bpmn', 'localName': 'SubChoreography', 'name': 'bpmn:SubChoreography'}

class SubProcess(Activity, FlowElementsContainer, InteractionNode):
    triggeredByEvent: cmof.Boolean
    _contents: List[Artifact]
    _ns={'prefix': 'bpmn', 'localName': 'SubProcess', 'name': 'bpmn:SubProcess'}

class Task(Activity, InteractionNode):
    _ns={'prefix': 'bpmn', 'localName': 'Task', 'name': 'bpmn:Task'}

class ThrowEvent(Event):
    _contents: Union[InputSet, List[DataInputAssociation], List[DataInput], List[EventDefinition], List[cmof.Ref[EventDefinition]]]
    _ns={'prefix': 'bpmn', 'localName': 'ThrowEvent', 'name': 'bpmn:ThrowEvent'}

class AdHocSubProcess(SubProcess):
    cancelRemainingInstances: cmof.Boolean
    ordering: AdHocOrdering
    _contents: Expression
    _ns={'prefix': 'bpmn', 'localName': 'AdHocSubProcess', 'name': 'bpmn:AdHocSubProcess'}

class BoundaryEvent(CatchEvent):
    attachedToRef: Activity
    cancelActivity: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'BoundaryEvent', 'name': 'bpmn:BoundaryEvent'}

class BusinessRuleTask(Task):
    implementation: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'BusinessRuleTask', 'name': 'bpmn:BusinessRuleTask'}

class EndEvent(ThrowEvent):
    _ns={'prefix': 'bpmn', 'localName': 'EndEvent', 'name': 'bpmn:EndEvent'}

class ImplicitThrowEvent(ThrowEvent):
    _ns={'prefix': 'bpmn', 'localName': 'ImplicitThrowEvent', 'name': 'bpmn:ImplicitThrowEvent'}

class IntermediateCatchEvent(CatchEvent):
    _ns={'prefix': 'bpmn', 'localName': 'IntermediateCatchEvent', 'name': 'bpmn:IntermediateCatchEvent'}

class IntermediateThrowEvent(ThrowEvent):
    _ns={'prefix': 'bpmn', 'localName': 'IntermediateThrowEvent', 'name': 'bpmn:IntermediateThrowEvent'}

class ManualTask(Task):
    _ns={'prefix': 'bpmn', 'localName': 'ManualTask', 'name': 'bpmn:ManualTask'}

class ReceiveTask(Task):
    implementation: cmof.String
    instantiate: cmof.Boolean
    messageRef: Message
    operationRef: Operation
    _ns={'prefix': 'bpmn', 'localName': 'ReceiveTask', 'name': 'bpmn:ReceiveTask'}

class ScriptTask(Task):
    scriptFormat: cmof.String
    _contents: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'ScriptTask', 'name': 'bpmn:ScriptTask'}

class SendTask(Task):
    implementation: cmof.String
    messageRef: Message
    operationRef: Operation
    _ns={'prefix': 'bpmn', 'localName': 'SendTask', 'name': 'bpmn:SendTask'}

class ServiceTask(Task):
    implementation: cmof.String
    operationRef: Operation
    _ns={'prefix': 'bpmn', 'localName': 'ServiceTask', 'name': 'bpmn:ServiceTask'}

class StartEvent(CatchEvent):
    isInterrupting: cmof.Boolean
    _ns={'prefix': 'bpmn', 'localName': 'StartEvent', 'name': 'bpmn:StartEvent'}

class Transaction(SubProcess):
    method: cmof.String
    protocol: cmof.String
    _ns={'prefix': 'bpmn', 'localName': 'Transaction', 'name': 'bpmn:Transaction'}

class UserTask(Task):
    implementation: cmof.String
    _contents: List[Rendering]
    _ns={'prefix': 'bpmn', 'localName': 'UserTask', 'name': 'bpmn:UserTask'}

class ActivationCondition(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:activationCondition', 'prefix': 'bpmn', 'localName': 'activationCondition'}

class Artifacts(cmof.Property):
    value: Artifact
    _ns={'name': 'bpmn:artifacts', 'prefix': 'bpmn', 'localName': 'artifacts'}

class Assignment(cmof.Property):
    value: Assignment
    _ns={'name': 'bpmn:assignment', 'prefix': 'bpmn', 'localName': 'assignment'}

class Auditing(cmof.Property):
    value: Auditing
    _ns={'name': 'bpmn:auditing', 'prefix': 'bpmn', 'localName': 'auditing'}

class Body(cmof.Property):
    value: cmof.String
    _ns={'name': 'bpmn:body', 'prefix': 'bpmn', 'localName': 'body'}

class BoundaryEventRefs(cmof.Property):
    value: BoundaryEvent
    _ns={'name': 'bpmn:boundaryEventRefs', 'prefix': 'bpmn', 'localName': 'boundaryEventRefs'}

class CategorizedFlowElements(cmof.Property):
    value: FlowElement
    _ns={'name': 'bpmn:categorizedFlowElements', 'prefix': 'bpmn', 'localName': 'categorizedFlowElements'}

class CategoryValue(cmof.Property):
    value: CategoryValue
    _ns={'name': 'bpmn:categoryValue', 'prefix': 'bpmn', 'localName': 'categoryValue'}

class CategoryValueRef(cmof.Property):
    value: CategoryValue
    _ns={'name': 'bpmn:categoryValueRef', 'prefix': 'bpmn', 'localName': 'categoryValueRef'}

class ChildLaneSet(cmof.Property):
    value: LaneSet
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:childLaneSet', 'prefix': 'bpmn', 'localName': 'childLaneSet'}

class ChoreographyRef(cmof.Property):
    value: Choreography
    _ns={'name': 'bpmn:choreographyRef', 'prefix': 'bpmn', 'localName': 'choreographyRef'}

class CompletionCondition(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:completionCondition', 'prefix': 'bpmn', 'localName': 'completionCondition'}

class ComplexBehaviorDefinition(cmof.Property):
    value: ComplexBehaviorDefinition
    _ns={'name': 'bpmn:complexBehaviorDefinition', 'prefix': 'bpmn', 'localName': 'complexBehaviorDefinition'}

class Condition(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:condition', 'prefix': 'bpmn', 'localName': 'condition'}

class ConditionExpression(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:conditionExpression', 'prefix': 'bpmn', 'localName': 'conditionExpression'}

class ConversationAssociations(cmof.Property):
    value: ConversationAssociation
    _ns={'name': 'bpmn:conversationAssociations', 'prefix': 'bpmn', 'localName': 'conversationAssociations'}

class ConversationLinks(cmof.Property):
    value: ConversationLink
    _ns={'name': 'bpmn:conversationLinks', 'prefix': 'bpmn', 'localName': 'conversationLinks'}

class ConversationNodes(cmof.Property):
    value: ConversationNode
    _ns={'name': 'bpmn:conversationNodes', 'prefix': 'bpmn', 'localName': 'conversationNodes'}

class Conversations(cmof.Property):
    value: ConversationNode
    _ns={'name': 'bpmn:conversations', 'prefix': 'bpmn', 'localName': 'conversations'}

class CorrelationKeys(cmof.Property):
    value: CorrelationKey
    _ns={'name': 'bpmn:correlationKeys', 'prefix': 'bpmn', 'localName': 'correlationKeys'}

class CorrelationPropertyBinding(cmof.Property):
    value: CorrelationPropertyBinding
    _ns={'name': 'bpmn:correlationPropertyBinding', 'prefix': 'bpmn', 'localName': 'correlationPropertyBinding'}

class CorrelationPropertyRef(cmof.Property):
    value: CorrelationProperty
    _ns={'name': 'bpmn:correlationPropertyRef', 'prefix': 'bpmn', 'localName': 'correlationPropertyRef'}

class CorrelationPropertyRetrievalExpression(cmof.Property):
    value: CorrelationPropertyRetrievalExpression
    _ns={'name': 'bpmn:correlationPropertyRetrievalExpression', 'prefix': 'bpmn', 'localName': 'correlationPropertyRetrievalExpression'}

class CorrelationSubscriptions(cmof.Property):
    value: CorrelationSubscription
    _ns={'name': 'bpmn:correlationSubscriptions', 'prefix': 'bpmn', 'localName': 'correlationSubscriptions'}

class DataInputAssociations(cmof.Property):
    value: DataInputAssociation
    _ns={'name': 'bpmn:dataInputAssociations', 'prefix': 'bpmn', 'localName': 'dataInputAssociations'}

class DataInputRefs(cmof.Property):
    value: DataInput
    _ns={'name': 'bpmn:dataInputRefs', 'prefix': 'bpmn', 'localName': 'dataInputRefs'}

class DataInputs(cmof.Property):
    value: DataInput
    _ns={'name': 'bpmn:dataInputs', 'prefix': 'bpmn', 'localName': 'dataInputs'}

class DataOutputAssociations(cmof.Property):
    value: DataOutputAssociation
    _ns={'name': 'bpmn:dataOutputAssociations', 'prefix': 'bpmn', 'localName': 'dataOutputAssociations'}

class DataOutputRefs(cmof.Property):
    value: DataOutput
    _ns={'name': 'bpmn:dataOutputRefs', 'prefix': 'bpmn', 'localName': 'dataOutputRefs'}

class DataOutputs(cmof.Property):
    value: DataOutput
    _ns={'name': 'bpmn:dataOutputs', 'prefix': 'bpmn', 'localName': 'dataOutputs'}

class DataPath(cmof.Property):
    value: FormalExpression
    _ns={'name': 'bpmn:dataPath', 'prefix': 'bpmn', 'localName': 'dataPath'}

class DataState(cmof.Property):
    value: DataState
    _ns={'name': 'bpmn:dataState', 'prefix': 'bpmn', 'localName': 'dataState'}

class Diagrams(cmof.Property):
    value: 'bpmndi.BPMNDiagram'
    _ns={'name': 'bpmn:diagrams', 'prefix': 'bpmn', 'localName': 'diagrams'}

class Documentation(cmof.Property):
    value: Documentation
    _ns={'name': 'bpmn:documentation', 'prefix': 'bpmn', 'localName': 'documentation'}

class EndPointRefs(cmof.Property):
    value: EndPoint
    _ns={'name': 'bpmn:endPointRefs', 'prefix': 'bpmn', 'localName': 'endPointRefs'}

class ErrorRef(cmof.Property):
    value: Error
    _ns={'name': 'bpmn:errorRef', 'prefix': 'bpmn', 'localName': 'errorRef'}

class Event(cmof.Property):
    value: ImplicitThrowEvent
    _ns={'name': 'bpmn:event', 'prefix': 'bpmn', 'localName': 'event'}

class EventDefinitionRef(cmof.Property):
    value: EventDefinition
    _ns={'name': 'bpmn:eventDefinitionRef', 'prefix': 'bpmn', 'localName': 'eventDefinitionRef'}

class EventDefinitions(cmof.Property):
    value: EventDefinition
    _ns={'name': 'bpmn:eventDefinitions', 'prefix': 'bpmn', 'localName': 'eventDefinitions'}

class Expression(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:expression', 'prefix': 'bpmn', 'localName': 'expression'}

class ExtensionAttributeDefinitions(cmof.Property):
    value: ExtensionAttributeDefinition
    _ns={'name': 'bpmn:extensionAttributeDefinitions', 'prefix': 'bpmn', 'localName': 'extensionAttributeDefinitions'}

class ExtensionDefinitions(cmof.Property):
    value: ExtensionDefinition
    _ns={'name': 'bpmn:extensionDefinitions', 'prefix': 'bpmn', 'localName': 'extensionDefinitions'}

class ExtensionElements(cmof.Property):
    value: ExtensionElements
    _ns={'name': 'bpmn:extensionElements', 'prefix': 'bpmn', 'localName': 'extensionElements'}

class Extensions(cmof.Property):
    value: Extension
    _ns={'name': 'bpmn:extensions', 'prefix': 'bpmn', 'localName': 'extensions'}

class FlowElements(cmof.Property):
    value: FlowElement
    _ns={'name': 'bpmn:flowElements', 'prefix': 'bpmn', 'localName': 'flowElements'}

class FlowNodeRef(cmof.Property):
    value: FlowNode
    _ns={'name': 'bpmn:flowNodeRef', 'prefix': 'bpmn', 'localName': 'flowNodeRef'}

class From(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:from', 'prefix': 'bpmn', 'localName': 'from'}

class Imports(cmof.Property):
    value: Import
    _ns={'name': 'bpmn:imports', 'prefix': 'bpmn', 'localName': 'imports'}

class InMessageRef(cmof.Property):
    value: Message
    _ns={'name': 'bpmn:inMessageRef', 'prefix': 'bpmn', 'localName': 'inMessageRef'}

class Incoming(cmof.Property):
    value: SequenceFlow
    _ns={'name': 'bpmn:incoming', 'prefix': 'bpmn', 'localName': 'incoming'}

class IncomingConversationLinks(cmof.Property):
    value: ConversationLink
    _ns={'name': 'bpmn:incomingConversationLinks', 'prefix': 'bpmn', 'localName': 'incomingConversationLinks'}

class InputDataItem(cmof.Property):
    value: DataInput
    _xml={'serialize': 'property'}
    _ns={'name': 'bpmn:inputDataItem', 'prefix': 'bpmn', 'localName': 'inputDataItem'}

class InputSet(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSet', 'prefix': 'bpmn', 'localName': 'inputSet'}

class InputSetRef(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSetRef', 'prefix': 'bpmn', 'localName': 'inputSetRef'}

class InputSetRefs(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSetRefs', 'prefix': 'bpmn', 'localName': 'inputSetRefs'}

class InputSetWithOptional(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSetWithOptional', 'prefix': 'bpmn', 'localName': 'inputSetWithOptional'}

class InputSetWithWhileExecuting(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSetWithWhileExecuting', 'prefix': 'bpmn', 'localName': 'inputSetWithWhileExecuting'}

class InputSets(cmof.Property):
    value: InputSet
    _ns={'name': 'bpmn:inputSets', 'prefix': 'bpmn', 'localName': 'inputSets'}

class InterfaceRef(cmof.Property):
    value: Interface
    _ns={'name': 'bpmn:interfaceRef', 'prefix': 'bpmn', 'localName': 'interfaceRef'}

class IoBinding(cmof.Property):
    value: InputOutputBinding
    _xml={'serialize': 'property'}
    _ns={'name': 'bpmn:ioBinding', 'prefix': 'bpmn', 'localName': 'ioBinding'}

class IoSpecification(cmof.Property):
    value: InputOutputSpecification
    _xml={'serialize': 'property'}
    _ns={'name': 'bpmn:ioSpecification', 'prefix': 'bpmn', 'localName': 'ioSpecification'}

class LaneSets(cmof.Property):
    value: LaneSet
    _ns={'name': 'bpmn:laneSets', 'prefix': 'bpmn', 'localName': 'laneSets'}

class Lanes(cmof.Property):
    value: Lane
    _ns={'name': 'bpmn:lanes', 'prefix': 'bpmn', 'localName': 'lanes'}

class LoopCardinality(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:loopCardinality', 'prefix': 'bpmn', 'localName': 'loopCardinality'}

class LoopCharacteristics(cmof.Property):
    value: LoopCharacteristics
    _ns={'name': 'bpmn:loopCharacteristics', 'prefix': 'bpmn', 'localName': 'loopCharacteristics'}

class LoopCondition(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:loopCondition', 'prefix': 'bpmn', 'localName': 'loopCondition'}

class LoopDataInputRef(cmof.Property):
    value: ItemAwareElement
    _ns={'name': 'bpmn:loopDataInputRef', 'prefix': 'bpmn', 'localName': 'loopDataInputRef'}

class LoopDataOutputRef(cmof.Property):
    value: ItemAwareElement
    _ns={'name': 'bpmn:loopDataOutputRef', 'prefix': 'bpmn', 'localName': 'loopDataOutputRef'}

class MessageFlowAssociations(cmof.Property):
    value: MessageFlowAssociation
    _ns={'name': 'bpmn:messageFlowAssociations', 'prefix': 'bpmn', 'localName': 'messageFlowAssociations'}

class MessageFlowRef(cmof.Property):
    value: MessageFlow
    _ns={'name': 'bpmn:messageFlowRef', 'prefix': 'bpmn', 'localName': 'messageFlowRef'}

class MessageFlowRefs(cmof.Property):
    value: MessageFlow
    _ns={'name': 'bpmn:messageFlowRefs', 'prefix': 'bpmn', 'localName': 'messageFlowRefs'}

class MessageFlows(cmof.Property):
    value: MessageFlow
    _ns={'name': 'bpmn:messageFlows', 'prefix': 'bpmn', 'localName': 'messageFlows'}

class MessagePath(cmof.Property):
    value: FormalExpression
    _ns={'name': 'bpmn:messagePath', 'prefix': 'bpmn', 'localName': 'messagePath'}

class Monitoring(cmof.Property):
    value: Monitoring
    _ns={'name': 'bpmn:monitoring', 'prefix': 'bpmn', 'localName': 'monitoring'}

class Operations(cmof.Property):
    value: Operation
    _ns={'name': 'bpmn:operations', 'prefix': 'bpmn', 'localName': 'operations'}

class OptionalInputRefs(cmof.Property):
    value: DataInput
    _ns={'name': 'bpmn:optionalInputRefs', 'prefix': 'bpmn', 'localName': 'optionalInputRefs'}

class OptionalOutputRefs(cmof.Property):
    value: DataOutput
    _ns={'name': 'bpmn:optionalOutputRefs', 'prefix': 'bpmn', 'localName': 'optionalOutputRefs'}

class OutMessageRef(cmof.Property):
    value: Message
    _ns={'name': 'bpmn:outMessageRef', 'prefix': 'bpmn', 'localName': 'outMessageRef'}

class Outgoing(cmof.Property):
    value: SequenceFlow
    _ns={'name': 'bpmn:outgoing', 'prefix': 'bpmn', 'localName': 'outgoing'}

class OutgoingConversationLinks(cmof.Property):
    value: ConversationLink
    _ns={'name': 'bpmn:outgoingConversationLinks', 'prefix': 'bpmn', 'localName': 'outgoingConversationLinks'}

class OutputDataItem(cmof.Property):
    value: DataOutput
    _xml={'serialize': 'property'}
    _ns={'name': 'bpmn:outputDataItem', 'prefix': 'bpmn', 'localName': 'outputDataItem'}

class OutputSet(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSet', 'prefix': 'bpmn', 'localName': 'outputSet'}

class OutputSetRef(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSetRef', 'prefix': 'bpmn', 'localName': 'outputSetRef'}

class OutputSetRefs(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSetRefs', 'prefix': 'bpmn', 'localName': 'outputSetRefs'}

class OutputSetWithOptional(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSetWithOptional', 'prefix': 'bpmn', 'localName': 'outputSetWithOptional'}

class OutputSetWithWhileExecuting(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSetWithWhileExecuting', 'prefix': 'bpmn', 'localName': 'outputSetWithWhileExecuting'}

class OutputSets(cmof.Property):
    value: OutputSet
    _ns={'name': 'bpmn:outputSets', 'prefix': 'bpmn', 'localName': 'outputSets'}

class ParticipantAssociations(cmof.Property):
    value: ParticipantAssociation
    _ns={'name': 'bpmn:participantAssociations', 'prefix': 'bpmn', 'localName': 'participantAssociations'}

class ParticipantMultiplicity(cmof.Property):
    value: ParticipantMultiplicity
    _ns={'name': 'bpmn:participantMultiplicity', 'prefix': 'bpmn', 'localName': 'participantMultiplicity'}

class ParticipantRef(cmof.Property):
    value: Participant
    _ns={'name': 'bpmn:participantRef', 'prefix': 'bpmn', 'localName': 'participantRef'}

class Participants(cmof.Property):
    value: Participant
    _ns={'name': 'bpmn:participants', 'prefix': 'bpmn', 'localName': 'participants'}

class PartitionElement(cmof.Property):
    value: BaseElement
    _ns={'name': 'bpmn:partitionElement', 'prefix': 'bpmn', 'localName': 'partitionElement'}

class Properties(cmof.Property):
    value: Property
    _ns={'name': 'bpmn:properties', 'prefix': 'bpmn', 'localName': 'properties'}

class Relationships(cmof.Property):
    value: Relationship
    _ns={'name': 'bpmn:relationships', 'prefix': 'bpmn', 'localName': 'relationships'}

class Renderings(cmof.Property):
    value: Rendering
    _ns={'name': 'bpmn:renderings', 'prefix': 'bpmn', 'localName': 'renderings'}

class ResourceAssignmentExpression(cmof.Property):
    value: ResourceAssignmentExpression
    _ns={'name': 'bpmn:resourceAssignmentExpression', 'prefix': 'bpmn', 'localName': 'resourceAssignmentExpression'}

class ResourceParameterBindings(cmof.Property):
    value: ResourceParameterBinding
    _ns={'name': 'bpmn:resourceParameterBindings', 'prefix': 'bpmn', 'localName': 'resourceParameterBindings'}

class ResourceParameters(cmof.Property):
    value: ResourceParameter
    _ns={'name': 'bpmn:resourceParameters', 'prefix': 'bpmn', 'localName': 'resourceParameters'}

class ResourceRef(cmof.Property):
    value: Resource
    _ns={'name': 'bpmn:resourceRef', 'prefix': 'bpmn', 'localName': 'resourceRef'}

class Resources(cmof.Property):
    value: ResourceRole
    _ns={'name': 'bpmn:resources', 'prefix': 'bpmn', 'localName': 'resources'}

class RootElements(cmof.Property):
    value: RootElement
    _ns={'name': 'bpmn:rootElements', 'prefix': 'bpmn', 'localName': 'rootElements'}

class Script(cmof.Property):
    value: cmof.String
    _ns={'name': 'bpmn:script', 'prefix': 'bpmn', 'localName': 'script'}

class Source(cmof.Property):
    value: LinkEventDefinition
    _ns={'name': 'bpmn:source', 'prefix': 'bpmn', 'localName': 'source'}

class SourceRef(cmof.Property):
    value: ItemAwareElement
    _ns={'name': 'bpmn:sourceRef', 'prefix': 'bpmn', 'localName': 'sourceRef'}

class SupportedInterfaceRef(cmof.Property):
    value: Interface
    _ns={'name': 'bpmn:supportedInterfaceRef', 'prefix': 'bpmn', 'localName': 'supportedInterfaceRef'}

class Supports(cmof.Property):
    value: Process
    _ns={'name': 'bpmn:supports', 'prefix': 'bpmn', 'localName': 'supports'}

class Target(cmof.Property):
    value: cmof.Element
    _ns={'name': 'bpmn:target', 'prefix': 'bpmn', 'localName': 'target'}

class TargetRef(cmof.Property):
    value: ItemAwareElement
    _ns={'name': 'bpmn:targetRef', 'prefix': 'bpmn', 'localName': 'targetRef'}

class Text(cmof.Property):
    value: cmof.String
    _ns={'name': 'bpmn:text', 'prefix': 'bpmn', 'localName': 'text'}

class TimeCycle(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:timeCycle', 'prefix': 'bpmn', 'localName': 'timeCycle'}

class TimeDate(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:timeDate', 'prefix': 'bpmn', 'localName': 'timeDate'}

class TimeDuration(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:timeDuration', 'prefix': 'bpmn', 'localName': 'timeDuration'}

class To(cmof.Property):
    value: Expression
    _xml={'serialize': 'xsi:type'}
    _ns={'name': 'bpmn:to', 'prefix': 'bpmn', 'localName': 'to'}

class Transformation(cmof.Property):
    value: FormalExpression
    _xml={'serialize': 'property'}
    _ns={'name': 'bpmn:transformation', 'prefix': 'bpmn', 'localName': 'transformation'}

class Values(cmof.Property):
    value: cmof.Element
    _ns={'name': 'bpmn:values', 'prefix': 'bpmn', 'localName': 'values'}

class WhileExecutingInputRefs(cmof.Property):
    value: DataInput
    _ns={'name': 'bpmn:whileExecutingInputRefs', 'prefix': 'bpmn', 'localName': 'whileExecutingInputRefs'}

class WhileExecutingOutputRefs(cmof.Property):
    value: DataOutput
    _ns={'name': 'bpmn:whileExecutingOutputRefs', 'prefix': 'bpmn', 'localName': 'whileExecutingOutputRefs'}

PACKAGE_METADATA = {'associations': [],
 'enumerations': [{'literalValues': [{'name': 'None'}, {'name': 'Public'},
                                     {'name': 'Private'}],
                   'name': 'ProcessType'},
                  {'literalValues': [{'name': 'Unspecified'},
                                     {'name': 'Converging'},
                                     {'name': 'Diverging'}, {'name': 'Mixed'}],
                   'name': 'GatewayDirection'},
                  {'literalValues': [{'name': 'Parallel'},
                                     {'name': 'Exclusive'}],
                   'name': 'EventBasedGatewayType'},
                  {'literalValues': [{'name': 'None'}, {'name': 'Forward'},
                                     {'name': 'Backward'}, {'name': 'Both'}],
                   'name': 'RelationshipDirection'},
                  {'literalValues': [{'name': 'Physical'},
                                     {'name': 'Information'}],
                   'name': 'ItemKind'},
                  {'literalValues': [{'name': 'None'}, {'name': 'Standard'},
                                     {'name': 'MultiInstanceSequential'},
                                     {'name': 'MultiInstanceParallel'}],
                   'name': 'ChoreographyLoopType'},
                  {'literalValues': [{'name': 'None'}, {'name': 'One'},
                                     {'name': 'Both'}],
                   'name': 'AssociationDirection'},
                  {'literalValues': [{'name': 'None'}, {'name': 'One'},
                                     {'name': 'All'}, {'name': 'Complex'}],
                   'name': 'MultiInstanceBehavior'},
                  {'literalValues': [{'name': 'Parallel'},
                                     {'name': 'Sequential'}],
                   'name': 'AdHocOrdering'}],
 'name': 'BPMN20',
 'prefix': 'bpmn',
 'types': [{'name': 'Interface',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:operations',
                            'ns': {'localName': 'operations',
                                   'name': 'bpmn:operations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'},
                           {'isAttr': True,
                            'name': 'bpmn:implementationRef',
                            'ns': {'localName': 'implementationRef',
                                   'name': 'bpmn:implementationRef',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['RootElement']},
           {'name': 'Operation',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isReference': True,
                            'name': 'bpmn:inMessageRef',
                            'ns': {'localName': 'inMessageRef',
                                   'name': 'bpmn:inMessageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'},
                           {'isReference': True,
                            'name': 'bpmn:outMessageRef',
                            'ns': {'localName': 'outMessageRef',
                                   'name': 'bpmn:outMessageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:errorRef',
                            'ns': {'localName': 'errorRef',
                                   'name': 'bpmn:errorRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Error'},
                           {'isAttr': True,
                            'name': 'bpmn:implementationRef',
                            'ns': {'localName': 'implementationRef',
                                   'name': 'bpmn:implementationRef',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'EndPoint', 'superClass': ['RootElement']},
           {'name': 'Auditing', 'superClass': ['BaseElement']},
           {'name': 'GlobalTask',
            'properties': [{'isMany': True,
                            'name': 'bpmn:resources',
                            'ns': {'localName': 'resources',
                                   'name': 'bpmn:resources',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceRole'}],
            'superClass': ['CallableElement']},
           {'name': 'Monitoring', 'superClass': ['BaseElement']},
           {'name': 'Performer', 'superClass': ['ResourceRole']},
           {'name': 'Process',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:processType',
                            'ns': {'localName': 'processType',
                                   'name': 'bpmn:processType',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ProcessType'},
                           {'isAttr': True,
                            'name': 'bpmn:isClosed',
                            'ns': {'localName': 'isClosed',
                                   'name': 'bpmn:isClosed',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'name': 'bpmn:auditing',
                            'ns': {'localName': 'auditing',
                                   'name': 'bpmn:auditing',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Auditing'},
                           {'name': 'bpmn:monitoring',
                            'ns': {'localName': 'monitoring',
                                   'name': 'bpmn:monitoring',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Monitoring'},
                           {'isMany': True,
                            'name': 'bpmn:properties',
                            'ns': {'localName': 'properties',
                                   'name': 'bpmn:properties',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Property'},
                           {'isMany': True,
                            'name': 'bpmn:laneSets',
                            'ns': {'localName': 'laneSets',
                                   'name': 'bpmn:laneSets',
                                   'prefix': 'bpmn'},
                            'replaces': 'FlowElementsContainer#laneSets',
                            'type': 'bpmn:LaneSet'},
                           {'isMany': True,
                            'name': 'bpmn:flowElements',
                            'ns': {'localName': 'flowElements',
                                   'name': 'bpmn:flowElements',
                                   'prefix': 'bpmn'},
                            'replaces': 'FlowElementsContainer#flowElements',
                            'type': 'bpmn:FlowElement'},
                           {'isMany': True,
                            'name': 'bpmn:artifacts',
                            'ns': {'localName': 'artifacts',
                                   'name': 'bpmn:artifacts',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Artifact'},
                           {'isMany': True,
                            'name': 'bpmn:resources',
                            'ns': {'localName': 'resources',
                                   'name': 'bpmn:resources',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceRole'},
                           {'isMany': True,
                            'name': 'bpmn:correlationSubscriptions',
                            'ns': {'localName': 'correlationSubscriptions',
                                   'name': 'bpmn:correlationSubscriptions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationSubscription'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:supports',
                            'ns': {'localName': 'supports',
                                   'name': 'bpmn:supports',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Process'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:definitionalCollaborationRef',
                            'ns': {'localName': 'definitionalCollaborationRef',
                                   'name': 'bpmn:definitionalCollaborationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Collaboration'},
                           {'isAttr': True,
                            'name': 'bpmn:isExecutable',
                            'ns': {'localName': 'isExecutable',
                                   'name': 'bpmn:isExecutable',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'}],
            'superClass': ['FlowElementsContainer', 'CallableElement']},
           {'name': 'LaneSet',
            'properties': [{'isMany': True,
                            'name': 'bpmn:lanes',
                            'ns': {'localName': 'lanes',
                                   'name': 'bpmn:lanes',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Lane'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'Lane',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:partitionElementRef',
                            'ns': {'localName': 'partitionElementRef',
                                   'name': 'bpmn:partitionElementRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:BaseElement'},
                           {'name': 'bpmn:partitionElement',
                            'ns': {'localName': 'partitionElement',
                                   'name': 'bpmn:partitionElement',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:BaseElement'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:flowNodeRef',
                            'ns': {'localName': 'flowNodeRef',
                                   'name': 'bpmn:flowNodeRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FlowNode'},
                           {'name': 'bpmn:childLaneSet',
                            'ns': {'localName': 'childLaneSet',
                                   'name': 'bpmn:childLaneSet',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:LaneSet',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['BaseElement']},
           {'name': 'GlobalManualTask', 'superClass': ['GlobalTask']},
           {'name': 'ManualTask', 'superClass': ['Task']},
           {'name': 'UserTask',
            'properties': [{'isMany': True,
                            'name': 'bpmn:renderings',
                            'ns': {'localName': 'renderings',
                                   'name': 'bpmn:renderings',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Rendering'},
                           {'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['Task']},
           {'name': 'Rendering', 'superClass': ['BaseElement']},
           {'name': 'HumanPerformer', 'superClass': ['Performer']},
           {'name': 'PotentialOwner', 'superClass': ['HumanPerformer']},
           {'name': 'GlobalUserTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:renderings',
                            'ns': {'localName': 'renderings',
                                   'name': 'bpmn:renderings',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Rendering'}],
            'superClass': ['GlobalTask']},
           {'isAbstract': True,
            'name': 'Gateway',
            'properties': [{'default': 'Unspecified',
                            'isAttr': True,
                            'name': 'bpmn:gatewayDirection',
                            'ns': {'localName': 'gatewayDirection',
                                   'name': 'bpmn:gatewayDirection',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:GatewayDirection'}],
            'superClass': ['FlowNode']},
           {'name': 'EventBasedGateway',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:instantiate',
                            'ns': {'localName': 'instantiate',
                                   'name': 'bpmn:instantiate',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'default': 'Exclusive',
                            'isAttr': True,
                            'name': 'bpmn:eventGatewayType',
                            'ns': {'localName': 'eventGatewayType',
                                   'name': 'bpmn:eventGatewayType',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventBasedGatewayType'}],
            'superClass': ['Gateway']},
           {'name': 'ComplexGateway',
            'properties': [{'name': 'bpmn:activationCondition',
                            'ns': {'localName': 'activationCondition',
                                   'name': 'bpmn:activationCondition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:default',
                            'ns': {'localName': 'default',
                                   'name': 'bpmn:default',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'}],
            'superClass': ['Gateway']},
           {'name': 'ExclusiveGateway',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:default',
                            'ns': {'localName': 'default',
                                   'name': 'bpmn:default',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'}],
            'superClass': ['Gateway']},
           {'name': 'InclusiveGateway',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:default',
                            'ns': {'localName': 'default',
                                   'name': 'bpmn:default',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'}],
            'superClass': ['Gateway']},
           {'name': 'ParallelGateway', 'superClass': ['Gateway']},
           {'isAbstract': True,
            'name': 'RootElement',
            'superClass': ['BaseElement']},
           {'name': 'Relationship',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:type',
                            'ns': {'localName': 'type',
                                   'name': 'bpmn:type',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:direction',
                            'ns': {'localName': 'direction',
                                   'name': 'bpmn:direction',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:RelationshipDirection'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:source',
                            'ns': {'localName': 'source',
                                   'name': 'bpmn:source',
                                   'prefix': 'bpmn'},
                            'type': 'Element'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:target',
                            'ns': {'localName': 'target',
                                   'name': 'bpmn:target',
                                   'prefix': 'bpmn'},
                            'type': 'Element'}],
            'superClass': ['BaseElement']},
           {'isAbstract': True,
            'name': 'BaseElement',
            'properties': [{'isAttr': True,
                            'isId': True,
                            'name': 'bpmn:id',
                            'ns': {'localName': 'id',
                                   'name': 'bpmn:id',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:documentation',
                            'ns': {'localName': 'documentation',
                                   'name': 'bpmn:documentation',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Documentation'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:extensionDefinitions',
                            'ns': {'localName': 'extensionDefinitions',
                                   'name': 'bpmn:extensionDefinitions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionDefinition'},
                           {'name': 'bpmn:extensionElements',
                            'ns': {'localName': 'extensionElements',
                                   'name': 'bpmn:extensionElements',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionElements'}]},
           {'name': 'Extension',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:mustUnderstand',
                            'ns': {'localName': 'mustUnderstand',
                                   'name': 'bpmn:mustUnderstand',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:definition',
                            'ns': {'localName': 'definition',
                                   'name': 'bpmn:definition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionDefinition'}]},
           {'name': 'ExtensionDefinition',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:extensionAttributeDefinitions',
                            'ns': {'localName': 'extensionAttributeDefinitions',
                                   'name': 'bpmn:extensionAttributeDefinitions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionAttributeDefinition'}]},
           {'name': 'ExtensionAttributeDefinition',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:type',
                            'ns': {'localName': 'type',
                                   'name': 'bpmn:type',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isReference',
                            'ns': {'localName': 'isReference',
                                   'name': 'bpmn:isReference',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:extensionDefinition',
                            'ns': {'localName': 'extensionDefinition',
                                   'name': 'bpmn:extensionDefinition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionDefinition'}]},
           {'name': 'ExtensionElements',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:valueRef',
                            'ns': {'localName': 'valueRef',
                                   'name': 'bpmn:valueRef',
                                   'prefix': 'bpmn'},
                            'type': 'Element'},
                           {'isMany': True,
                            'name': 'bpmn:values',
                            'ns': {'localName': 'values',
                                   'name': 'bpmn:values',
                                   'prefix': 'bpmn'},
                            'type': 'Element'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:extensionAttributeDefinition',
                            'ns': {'localName': 'extensionAttributeDefinition',
                                   'name': 'bpmn:extensionAttributeDefinition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ExtensionAttributeDefinition'}]},
           {'name': 'Documentation',
            'properties': [{'isBody': True,
                            'name': 'bpmn:text',
                            'ns': {'localName': 'text',
                                   'name': 'bpmn:text',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': 'text/plain',
                            'isAttr': True,
                            'name': 'bpmn:textFormat',
                            'ns': {'localName': 'textFormat',
                                   'name': 'bpmn:textFormat',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'isAbstract': True,
            'name': 'Event',
            'properties': [{'isMany': True,
                            'name': 'bpmn:properties',
                            'ns': {'localName': 'properties',
                                   'name': 'bpmn:properties',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Property'}],
            'superClass': ['FlowNode', 'InteractionNode']},
           {'name': 'IntermediateCatchEvent', 'superClass': ['CatchEvent']},
           {'name': 'IntermediateThrowEvent', 'superClass': ['ThrowEvent']},
           {'name': 'EndEvent', 'superClass': ['ThrowEvent']},
           {'name': 'StartEvent',
            'properties': [{'default': True,
                            'isAttr': True,
                            'name': 'bpmn:isInterrupting',
                            'ns': {'localName': 'isInterrupting',
                                   'name': 'bpmn:isInterrupting',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'}],
            'superClass': ['CatchEvent']},
           {'isAbstract': True,
            'name': 'ThrowEvent',
            'properties': [{'isMany': True,
                            'name': 'bpmn:dataInputs',
                            'ns': {'localName': 'dataInputs',
                                   'name': 'bpmn:dataInputs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput'},
                           {'isMany': True,
                            'name': 'bpmn:dataInputAssociations',
                            'ns': {'localName': 'dataInputAssociations',
                                   'name': 'bpmn:dataInputAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInputAssociation'},
                           {'name': 'bpmn:inputSet',
                            'ns': {'localName': 'inputSet',
                                   'name': 'bpmn:inputSet',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isMany': True,
                            'name': 'bpmn:eventDefinitions',
                            'ns': {'localName': 'eventDefinitions',
                                   'name': 'bpmn:eventDefinitions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:eventDefinitionRef',
                            'ns': {'localName': 'eventDefinitionRef',
                                   'name': 'bpmn:eventDefinitionRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'}],
            'superClass': ['Event']},
           {'isAbstract': True,
            'name': 'CatchEvent',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:parallelMultiple',
                            'ns': {'localName': 'parallelMultiple',
                                   'name': 'bpmn:parallelMultiple',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isMany': True,
                            'name': 'bpmn:dataOutputs',
                            'ns': {'localName': 'dataOutputs',
                                   'name': 'bpmn:dataOutputs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput'},
                           {'isMany': True,
                            'name': 'bpmn:dataOutputAssociations',
                            'ns': {'localName': 'dataOutputAssociations',
                                   'name': 'bpmn:dataOutputAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutputAssociation'},
                           {'name': 'bpmn:outputSet',
                            'ns': {'localName': 'outputSet',
                                   'name': 'bpmn:outputSet',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'},
                           {'isMany': True,
                            'name': 'bpmn:eventDefinitions',
                            'ns': {'localName': 'eventDefinitions',
                                   'name': 'bpmn:eventDefinitions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:eventDefinitionRef',
                            'ns': {'localName': 'eventDefinitionRef',
                                   'name': 'bpmn:eventDefinitionRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'}],
            'superClass': ['Event']},
           {'name': 'BoundaryEvent',
            'properties': [{'default': True,
                            'isAttr': True,
                            'name': 'bpmn:cancelActivity',
                            'ns': {'localName': 'cancelActivity',
                                   'name': 'bpmn:cancelActivity',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:attachedToRef',
                            'ns': {'localName': 'attachedToRef',
                                   'name': 'bpmn:attachedToRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Activity'}],
            'superClass': ['CatchEvent']},
           {'isAbstract': True,
            'name': 'EventDefinition',
            'superClass': ['RootElement']},
           {'name': 'CancelEventDefinition', 'superClass': ['EventDefinition']},
           {'name': 'ErrorEventDefinition',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:errorRef',
                            'ns': {'localName': 'errorRef',
                                   'name': 'bpmn:errorRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Error'}],
            'superClass': ['EventDefinition']},
           {'name': 'TerminateEventDefinition',
            'superClass': ['EventDefinition']},
           {'name': 'EscalationEventDefinition',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:escalationRef',
                            'ns': {'localName': 'escalationRef',
                                   'name': 'bpmn:escalationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Escalation'}],
            'superClass': ['EventDefinition']},
           {'name': 'Escalation',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:structureRef',
                            'ns': {'localName': 'structureRef',
                                   'name': 'bpmn:structureRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:escalationCode',
                            'ns': {'localName': 'escalationCode',
                                   'name': 'bpmn:escalationCode',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['RootElement']},
           {'name': 'CompensateEventDefinition',
            'properties': [{'default': True,
                            'isAttr': True,
                            'name': 'bpmn:waitForCompletion',
                            'ns': {'localName': 'waitForCompletion',
                                   'name': 'bpmn:waitForCompletion',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:activityRef',
                            'ns': {'localName': 'activityRef',
                                   'name': 'bpmn:activityRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Activity'}],
            'superClass': ['EventDefinition']},
           {'name': 'TimerEventDefinition',
            'properties': [{'name': 'bpmn:timeDate',
                            'ns': {'localName': 'timeDate',
                                   'name': 'bpmn:timeDate',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'name': 'bpmn:timeCycle',
                            'ns': {'localName': 'timeCycle',
                                   'name': 'bpmn:timeCycle',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'name': 'bpmn:timeDuration',
                            'ns': {'localName': 'timeDuration',
                                   'name': 'bpmn:timeDuration',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['EventDefinition']},
           {'name': 'LinkEventDefinition',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:target',
                            'ns': {'localName': 'target',
                                   'name': 'bpmn:target',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:LinkEventDefinition'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:source',
                            'ns': {'localName': 'source',
                                   'name': 'bpmn:source',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:LinkEventDefinition'}],
            'superClass': ['EventDefinition']},
           {'name': 'MessageEventDefinition',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:messageRef',
                            'ns': {'localName': 'messageRef',
                                   'name': 'bpmn:messageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:operationRef',
                            'ns': {'localName': 'operationRef',
                                   'name': 'bpmn:operationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'}],
            'superClass': ['EventDefinition']},
           {'name': 'ConditionalEventDefinition',
            'properties': [{'name': 'bpmn:condition',
                            'ns': {'localName': 'condition',
                                   'name': 'bpmn:condition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['EventDefinition']},
           {'name': 'SignalEventDefinition',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:signalRef',
                            'ns': {'localName': 'signalRef',
                                   'name': 'bpmn:signalRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Signal'}],
            'superClass': ['EventDefinition']},
           {'name': 'Signal',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:structureRef',
                            'ns': {'localName': 'structureRef',
                                   'name': 'bpmn:structureRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['RootElement']},
           {'name': 'ImplicitThrowEvent', 'superClass': ['ThrowEvent']},
           {'name': 'DataState',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'ItemAwareElement',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:itemSubjectRef',
                            'ns': {'localName': 'itemSubjectRef',
                                   'name': 'bpmn:itemSubjectRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'},
                           {'name': 'bpmn:dataState',
                            'ns': {'localName': 'dataState',
                                   'name': 'bpmn:dataState',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataState'}],
            'superClass': ['BaseElement']},
           {'name': 'DataAssociation',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:sourceRef',
                            'ns': {'localName': 'sourceRef',
                                   'name': 'bpmn:sourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemAwareElement'},
                           {'isReference': True,
                            'name': 'bpmn:targetRef',
                            'ns': {'localName': 'targetRef',
                                   'name': 'bpmn:targetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemAwareElement'},
                           {'name': 'bpmn:transformation',
                            'ns': {'localName': 'transformation',
                                   'name': 'bpmn:transformation',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FormalExpression',
                            'xml': {'serialize': 'property'}},
                           {'isMany': True,
                            'name': 'bpmn:assignment',
                            'ns': {'localName': 'assignment',
                                   'name': 'bpmn:assignment',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Assignment'}],
            'superClass': ['BaseElement']},
           {'name': 'DataInput',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isCollection',
                            'ns': {'localName': 'isCollection',
                                   'name': 'bpmn:isCollection',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:inputSetRef',
                            'ns': {'localName': 'inputSetRef',
                                   'name': 'bpmn:inputSetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:inputSetWithOptional',
                            'ns': {'localName': 'inputSetWithOptional',
                                   'name': 'bpmn:inputSetWithOptional',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:inputSetWithWhileExecuting',
                            'ns': {'localName': 'inputSetWithWhileExecuting',
                                   'name': 'bpmn:inputSetWithWhileExecuting',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'}],
            'superClass': ['ItemAwareElement']},
           {'name': 'DataOutput',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isCollection',
                            'ns': {'localName': 'isCollection',
                                   'name': 'bpmn:isCollection',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:outputSetRef',
                            'ns': {'localName': 'outputSetRef',
                                   'name': 'bpmn:outputSetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:outputSetWithOptional',
                            'ns': {'localName': 'outputSetWithOptional',
                                   'name': 'bpmn:outputSetWithOptional',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:outputSetWithWhileExecuting',
                            'ns': {'localName': 'outputSetWithWhileExecuting',
                                   'name': 'bpmn:outputSetWithWhileExecuting',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'}],
            'superClass': ['ItemAwareElement']},
           {'name': 'InputSet',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:dataInputRefs',
                            'ns': {'localName': 'dataInputRefs',
                                   'name': 'bpmn:dataInputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:optionalInputRefs',
                            'ns': {'localName': 'optionalInputRefs',
                                   'name': 'bpmn:optionalInputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:whileExecutingInputRefs',
                            'ns': {'localName': 'whileExecutingInputRefs',
                                   'name': 'bpmn:whileExecutingInputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:outputSetRefs',
                            'ns': {'localName': 'outputSetRefs',
                                   'name': 'bpmn:outputSetRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'}],
            'superClass': ['BaseElement']},
           {'name': 'OutputSet',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:dataOutputRefs',
                            'ns': {'localName': 'dataOutputRefs',
                                   'name': 'bpmn:dataOutputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:inputSetRefs',
                            'ns': {'localName': 'inputSetRefs',
                                   'name': 'bpmn:inputSetRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:optionalOutputRefs',
                            'ns': {'localName': 'optionalOutputRefs',
                                   'name': 'bpmn:optionalOutputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:whileExecutingOutputRefs',
                            'ns': {'localName': 'whileExecutingOutputRefs',
                                   'name': 'bpmn:whileExecutingOutputRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput'}],
            'superClass': ['BaseElement']},
           {'name': 'Property',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['ItemAwareElement']},
           {'name': 'DataInputAssociation', 'superClass': ['DataAssociation']},
           {'name': 'DataOutputAssociation', 'superClass': ['DataAssociation']},
           {'name': 'InputOutputSpecification',
            'properties': [{'isMany': True,
                            'name': 'bpmn:dataInputs',
                            'ns': {'localName': 'dataInputs',
                                   'name': 'bpmn:dataInputs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput'},
                           {'isMany': True,
                            'name': 'bpmn:dataOutputs',
                            'ns': {'localName': 'dataOutputs',
                                   'name': 'bpmn:dataOutputs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput'},
                           {'isMany': True,
                            'name': 'bpmn:inputSets',
                            'ns': {'localName': 'inputSets',
                                   'name': 'bpmn:inputSets',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isMany': True,
                            'name': 'bpmn:outputSets',
                            'ns': {'localName': 'outputSets',
                                   'name': 'bpmn:outputSets',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'}],
            'superClass': ['BaseElement']},
           {'name': 'DataObject',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isCollection',
                            'ns': {'localName': 'isCollection',
                                   'name': 'bpmn:isCollection',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'}],
            'superClass': ['FlowElement', 'ItemAwareElement']},
           {'name': 'InputOutputBinding',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:inputDataRef',
                            'ns': {'localName': 'inputDataRef',
                                   'name': 'bpmn:inputDataRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputSet'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:outputDataRef',
                            'ns': {'localName': 'outputDataRef',
                                   'name': 'bpmn:outputDataRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:OutputSet'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:operationRef',
                            'ns': {'localName': 'operationRef',
                                   'name': 'bpmn:operationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'}]},
           {'name': 'Assignment',
            'properties': [{'name': 'bpmn:from',
                            'ns': {'localName': 'from',
                                   'name': 'bpmn:from',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'name': 'bpmn:to',
                            'ns': {'localName': 'to',
                                   'name': 'bpmn:to',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['BaseElement']},
           {'name': 'DataStore',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:capacity',
                            'ns': {'localName': 'capacity',
                                   'name': 'bpmn:capacity',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'},
                           {'default': True,
                            'isAttr': True,
                            'name': 'bpmn:isUnlimited',
                            'ns': {'localName': 'isUnlimited',
                                   'name': 'bpmn:isUnlimited',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'}],
            'superClass': ['RootElement', 'ItemAwareElement']},
           {'name': 'DataStoreReference',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:dataStoreRef',
                            'ns': {'localName': 'dataStoreRef',
                                   'name': 'bpmn:dataStoreRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataStore'}],
            'superClass': ['ItemAwareElement', 'FlowElement']},
           {'name': 'DataObjectReference',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:dataObjectRef',
                            'ns': {'localName': 'dataObjectRef',
                                   'name': 'bpmn:dataObjectRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataObject'}],
            'superClass': ['ItemAwareElement', 'FlowElement']},
           {'name': 'ConversationLink',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:sourceRef',
                            'ns': {'localName': 'sourceRef',
                                   'name': 'bpmn:sourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InteractionNode'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:targetRef',
                            'ns': {'localName': 'targetRef',
                                   'name': 'bpmn:targetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InteractionNode'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'ConversationAssociation',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:innerConversationNodeRef',
                            'ns': {'localName': 'innerConversationNodeRef',
                                   'name': 'bpmn:innerConversationNodeRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationNode'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:outerConversationNodeRef',
                            'ns': {'localName': 'outerConversationNodeRef',
                                   'name': 'bpmn:outerConversationNodeRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationNode'}],
            'superClass': ['BaseElement']},
           {'name': 'CallConversation',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:calledCollaborationRef',
                            'ns': {'localName': 'calledCollaborationRef',
                                   'name': 'bpmn:calledCollaborationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Collaboration'},
                           {'isMany': True,
                            'name': 'bpmn:participantAssociations',
                            'ns': {'localName': 'participantAssociations',
                                   'name': 'bpmn:participantAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ParticipantAssociation'}],
            'superClass': ['ConversationNode']},
           {'name': 'Conversation', 'superClass': ['ConversationNode']},
           {'name': 'SubConversation',
            'properties': [{'isMany': True,
                            'name': 'bpmn:conversationNodes',
                            'ns': {'localName': 'conversationNodes',
                                   'name': 'bpmn:conversationNodes',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationNode'}],
            'superClass': ['ConversationNode']},
           {'isAbstract': True,
            'name': 'ConversationNode',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:participantRef',
                            'ns': {'localName': 'participantRef',
                                   'name': 'bpmn:participantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:messageFlowRefs',
                            'ns': {'localName': 'messageFlowRefs',
                                   'name': 'bpmn:messageFlowRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlow'},
                           {'isMany': True,
                            'name': 'bpmn:correlationKeys',
                            'ns': {'localName': 'correlationKeys',
                                   'name': 'bpmn:correlationKeys',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationKey'}],
            'superClass': ['InteractionNode', 'BaseElement']},
           {'name': 'GlobalConversation', 'superClass': ['Collaboration']},
           {'name': 'PartnerEntity',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:participantRef',
                            'ns': {'localName': 'participantRef',
                                   'name': 'bpmn:participantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'}],
            'superClass': ['RootElement']},
           {'name': 'PartnerRole',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:participantRef',
                            'ns': {'localName': 'participantRef',
                                   'name': 'bpmn:participantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'}],
            'superClass': ['RootElement']},
           {'name': 'CorrelationProperty',
            'properties': [{'isMany': True,
                            'name': 'bpmn:correlationPropertyRetrievalExpression',
                            'ns': {'localName': 'correlationPropertyRetrievalExpression',
                                   'name': 'bpmn:correlationPropertyRetrievalExpression',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationPropertyRetrievalExpression'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:type',
                            'ns': {'localName': 'type',
                                   'name': 'bpmn:type',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'}],
            'superClass': ['RootElement']},
           {'name': 'Error',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:structureRef',
                            'ns': {'localName': 'structureRef',
                                   'name': 'bpmn:structureRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:errorCode',
                            'ns': {'localName': 'errorCode',
                                   'name': 'bpmn:errorCode',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['RootElement']},
           {'name': 'CorrelationKey',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:correlationPropertyRef',
                            'ns': {'localName': 'correlationPropertyRef',
                                   'name': 'bpmn:correlationPropertyRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationProperty'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'isAbstract': False,
            'name': 'Expression',
            'properties': [{'isBody': True,
                            'name': 'bpmn:body',
                            'ns': {'localName': 'body',
                                   'name': 'bpmn:body',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'FormalExpression',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:language',
                            'ns': {'localName': 'language',
                                   'name': 'bpmn:language',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:evaluatesToTypeRef',
                            'ns': {'localName': 'evaluatesToTypeRef',
                                   'name': 'bpmn:evaluatesToTypeRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'}],
            'superClass': ['Expression']},
           {'name': 'Message',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:itemRef',
                            'ns': {'localName': 'itemRef',
                                   'name': 'bpmn:itemRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'}],
            'superClass': ['RootElement']},
           {'name': 'ItemDefinition',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:itemKind',
                            'ns': {'localName': 'itemKind',
                                   'name': 'bpmn:itemKind',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemKind'},
                           {'isAttr': True,
                            'name': 'bpmn:structureRef',
                            'ns': {'localName': 'structureRef',
                                   'name': 'bpmn:structureRef',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isCollection',
                            'ns': {'localName': 'isCollection',
                                   'name': 'bpmn:isCollection',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:import',
                            'ns': {'localName': 'import',
                                   'name': 'bpmn:import',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Import'}],
            'superClass': ['RootElement']},
           {'isAbstract': True,
            'name': 'FlowElement',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'name': 'bpmn:auditing',
                            'ns': {'localName': 'auditing',
                                   'name': 'bpmn:auditing',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Auditing'},
                           {'name': 'bpmn:monitoring',
                            'ns': {'localName': 'monitoring',
                                   'name': 'bpmn:monitoring',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Monitoring'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:categoryValueRef',
                            'ns': {'localName': 'categoryValueRef',
                                   'name': 'bpmn:categoryValueRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CategoryValue'}],
            'superClass': ['BaseElement']},
           {'name': 'SequenceFlow',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:isImmediate',
                            'ns': {'localName': 'isImmediate',
                                   'name': 'bpmn:isImmediate',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'name': 'bpmn:conditionExpression',
                            'ns': {'localName': 'conditionExpression',
                                   'name': 'bpmn:conditionExpression',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:sourceRef',
                            'ns': {'localName': 'sourceRef',
                                   'name': 'bpmn:sourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FlowNode'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:targetRef',
                            'ns': {'localName': 'targetRef',
                                   'name': 'bpmn:targetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FlowNode'}],
            'superClass': ['FlowElement']},
           {'isAbstract': True,
            'name': 'FlowElementsContainer',
            'properties': [{'isMany': True,
                            'name': 'bpmn:laneSets',
                            'ns': {'localName': 'laneSets',
                                   'name': 'bpmn:laneSets',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:LaneSet'},
                           {'isMany': True,
                            'name': 'bpmn:flowElements',
                            'ns': {'localName': 'flowElements',
                                   'name': 'bpmn:flowElements',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FlowElement'}],
            'superClass': ['BaseElement']},
           {'isAbstract': True,
            'name': 'CallableElement',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'name': 'bpmn:ioSpecification',
                            'ns': {'localName': 'ioSpecification',
                                   'name': 'bpmn:ioSpecification',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputOutputSpecification',
                            'xml': {'serialize': 'property'}},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:supportedInterfaceRef',
                            'ns': {'localName': 'supportedInterfaceRef',
                                   'name': 'bpmn:supportedInterfaceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Interface'},
                           {'isMany': True,
                            'name': 'bpmn:ioBinding',
                            'ns': {'localName': 'ioBinding',
                                   'name': 'bpmn:ioBinding',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputOutputBinding',
                            'xml': {'serialize': 'property'}}],
            'superClass': ['RootElement']},
           {'isAbstract': True,
            'name': 'FlowNode',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:incoming',
                            'ns': {'localName': 'incoming',
                                   'name': 'bpmn:incoming',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:outgoing',
                            'ns': {'localName': 'outgoing',
                                   'name': 'bpmn:outgoing',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:lanes',
                            'ns': {'localName': 'lanes',
                                   'name': 'bpmn:lanes',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Lane'}],
            'superClass': ['FlowElement']},
           {'name': 'CorrelationPropertyRetrievalExpression',
            'properties': [{'name': 'bpmn:messagePath',
                            'ns': {'localName': 'messagePath',
                                   'name': 'bpmn:messagePath',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FormalExpression'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:messageRef',
                            'ns': {'localName': 'messageRef',
                                   'name': 'bpmn:messageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'}],
            'superClass': ['BaseElement']},
           {'name': 'CorrelationPropertyBinding',
            'properties': [{'name': 'bpmn:dataPath',
                            'ns': {'localName': 'dataPath',
                                   'name': 'bpmn:dataPath',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FormalExpression'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:correlationPropertyRef',
                            'ns': {'localName': 'correlationPropertyRef',
                                   'name': 'bpmn:correlationPropertyRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationProperty'}],
            'superClass': ['BaseElement']},
           {'name': 'Resource',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:resourceParameters',
                            'ns': {'localName': 'resourceParameters',
                                   'name': 'bpmn:resourceParameters',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceParameter'}],
            'superClass': ['RootElement']},
           {'name': 'ResourceParameter',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:isRequired',
                            'ns': {'localName': 'isRequired',
                                   'name': 'bpmn:isRequired',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:type',
                            'ns': {'localName': 'type',
                                   'name': 'bpmn:type',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemDefinition'}],
            'superClass': ['BaseElement']},
           {'name': 'CorrelationSubscription',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:correlationKeyRef',
                            'ns': {'localName': 'correlationKeyRef',
                                   'name': 'bpmn:correlationKeyRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationKey'},
                           {'isMany': True,
                            'name': 'bpmn:correlationPropertyBinding',
                            'ns': {'localName': 'correlationPropertyBinding',
                                   'name': 'bpmn:correlationPropertyBinding',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationPropertyBinding'}],
            'superClass': ['BaseElement']},
           {'name': 'MessageFlow',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:sourceRef',
                            'ns': {'localName': 'sourceRef',
                                   'name': 'bpmn:sourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InteractionNode'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:targetRef',
                            'ns': {'localName': 'targetRef',
                                   'name': 'bpmn:targetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InteractionNode'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:messageRef',
                            'ns': {'localName': 'messageRef',
                                   'name': 'bpmn:messageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'}],
            'superClass': ['BaseElement']},
           {'name': 'MessageFlowAssociation',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:innerMessageFlowRef',
                            'ns': {'localName': 'innerMessageFlowRef',
                                   'name': 'bpmn:innerMessageFlowRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlow'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:outerMessageFlowRef',
                            'ns': {'localName': 'outerMessageFlowRef',
                                   'name': 'bpmn:outerMessageFlowRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlow'}],
            'superClass': ['BaseElement']},
           {'isAbstract': True,
            'name': 'InteractionNode',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:incomingConversationLinks',
                            'ns': {'localName': 'incomingConversationLinks',
                                   'name': 'bpmn:incomingConversationLinks',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationLink'},
                           {'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:outgoingConversationLinks',
                            'ns': {'localName': 'outgoingConversationLinks',
                                   'name': 'bpmn:outgoingConversationLinks',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationLink'}]},
           {'name': 'Participant',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:interfaceRef',
                            'ns': {'localName': 'interfaceRef',
                                   'name': 'bpmn:interfaceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Interface'},
                           {'name': 'bpmn:participantMultiplicity',
                            'ns': {'localName': 'participantMultiplicity',
                                   'name': 'bpmn:participantMultiplicity',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ParticipantMultiplicity'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:endPointRefs',
                            'ns': {'localName': 'endPointRefs',
                                   'name': 'bpmn:endPointRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EndPoint'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:processRef',
                            'ns': {'localName': 'processRef',
                                   'name': 'bpmn:processRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Process'}],
            'superClass': ['InteractionNode', 'BaseElement']},
           {'name': 'ParticipantAssociation',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:innerParticipantRef',
                            'ns': {'localName': 'innerParticipantRef',
                                   'name': 'bpmn:innerParticipantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:outerParticipantRef',
                            'ns': {'localName': 'outerParticipantRef',
                                   'name': 'bpmn:outerParticipantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'}],
            'superClass': ['BaseElement']},
           {'name': 'ParticipantMultiplicity',
            'properties': [{'default': 0,
                            'isAttr': True,
                            'name': 'bpmn:minimum',
                            'ns': {'localName': 'minimum',
                                   'name': 'bpmn:minimum',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'},
                           {'default': 1,
                            'isAttr': True,
                            'name': 'bpmn:maximum',
                            'ns': {'localName': 'maximum',
                                   'name': 'bpmn:maximum',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'}],
            'superClass': ['BaseElement']},
           {'name': 'Collaboration',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:isClosed',
                            'ns': {'localName': 'isClosed',
                                   'name': 'bpmn:isClosed',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isMany': True,
                            'name': 'bpmn:participants',
                            'ns': {'localName': 'participants',
                                   'name': 'bpmn:participants',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'},
                           {'isMany': True,
                            'name': 'bpmn:messageFlows',
                            'ns': {'localName': 'messageFlows',
                                   'name': 'bpmn:messageFlows',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlow'},
                           {'isMany': True,
                            'name': 'bpmn:artifacts',
                            'ns': {'localName': 'artifacts',
                                   'name': 'bpmn:artifacts',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Artifact'},
                           {'isMany': True,
                            'name': 'bpmn:conversations',
                            'ns': {'localName': 'conversations',
                                   'name': 'bpmn:conversations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationNode'},
                           {'name': 'bpmn:conversationAssociations',
                            'ns': {'localName': 'conversationAssociations',
                                   'name': 'bpmn:conversationAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationAssociation'},
                           {'isMany': True,
                            'name': 'bpmn:participantAssociations',
                            'ns': {'localName': 'participantAssociations',
                                   'name': 'bpmn:participantAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ParticipantAssociation'},
                           {'isMany': True,
                            'name': 'bpmn:messageFlowAssociations',
                            'ns': {'localName': 'messageFlowAssociations',
                                   'name': 'bpmn:messageFlowAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlowAssociation'},
                           {'isMany': True,
                            'name': 'bpmn:correlationKeys',
                            'ns': {'localName': 'correlationKeys',
                                   'name': 'bpmn:correlationKeys',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationKey'},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:choreographyRef',
                            'ns': {'localName': 'choreographyRef',
                                   'name': 'bpmn:choreographyRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Choreography'},
                           {'isMany': True,
                            'name': 'bpmn:conversationLinks',
                            'ns': {'localName': 'conversationLinks',
                                   'name': 'bpmn:conversationLinks',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ConversationLink'}],
            'superClass': ['RootElement']},
           {'isAbstract': True,
            'name': 'ChoreographyActivity',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:participantRef',
                            'ns': {'localName': 'participantRef',
                                   'name': 'bpmn:participantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:initiatingParticipantRef',
                            'ns': {'localName': 'initiatingParticipantRef',
                                   'name': 'bpmn:initiatingParticipantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'},
                           {'isMany': True,
                            'name': 'bpmn:correlationKeys',
                            'ns': {'localName': 'correlationKeys',
                                   'name': 'bpmn:correlationKeys',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CorrelationKey'},
                           {'default': 'None',
                            'isAttr': True,
                            'name': 'bpmn:loopType',
                            'ns': {'localName': 'loopType',
                                   'name': 'bpmn:loopType',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ChoreographyLoopType'}],
            'superClass': ['FlowNode']},
           {'name': 'CallChoreography',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:calledChoreographyRef',
                            'ns': {'localName': 'calledChoreographyRef',
                                   'name': 'bpmn:calledChoreographyRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Choreography'},
                           {'isMany': True,
                            'name': 'bpmn:participantAssociations',
                            'ns': {'localName': 'participantAssociations',
                                   'name': 'bpmn:participantAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ParticipantAssociation'}],
            'superClass': ['ChoreographyActivity']},
           {'name': 'SubChoreography',
            'properties': [{'isMany': True,
                            'name': 'bpmn:artifacts',
                            'ns': {'localName': 'artifacts',
                                   'name': 'bpmn:artifacts',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Artifact'}],
            'superClass': ['ChoreographyActivity', 'FlowElementsContainer']},
           {'name': 'ChoreographyTask',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:messageFlowRef',
                            'ns': {'localName': 'messageFlowRef',
                                   'name': 'bpmn:messageFlowRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MessageFlow'}],
            'superClass': ['ChoreographyActivity']},
           {'name': 'Choreography',
            'superClass': ['Collaboration', 'FlowElementsContainer']},
           {'name': 'GlobalChoreographyTask',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:initiatingParticipantRef',
                            'ns': {'localName': 'initiatingParticipantRef',
                                   'name': 'bpmn:initiatingParticipantRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Participant'}],
            'superClass': ['Choreography']},
           {'name': 'TextAnnotation',
            'properties': [{'name': 'bpmn:text',
                            'ns': {'localName': 'text',
                                   'name': 'bpmn:text',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': 'text/plain',
                            'isAttr': True,
                            'name': 'bpmn:textFormat',
                            'ns': {'localName': 'textFormat',
                                   'name': 'bpmn:textFormat',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['Artifact']},
           {'name': 'Group',
            'properties': [{'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:categoryValueRef',
                            'ns': {'localName': 'categoryValueRef',
                                   'name': 'bpmn:categoryValueRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CategoryValue'}],
            'superClass': ['Artifact']},
           {'name': 'Association',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:associationDirection',
                            'ns': {'localName': 'associationDirection',
                                   'name': 'bpmn:associationDirection',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:AssociationDirection'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:sourceRef',
                            'ns': {'localName': 'sourceRef',
                                   'name': 'bpmn:sourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:BaseElement'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:targetRef',
                            'ns': {'localName': 'targetRef',
                                   'name': 'bpmn:targetRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:BaseElement'}],
            'superClass': ['Artifact']},
           {'name': 'Category',
            'properties': [{'isMany': True,
                            'name': 'bpmn:categoryValue',
                            'ns': {'localName': 'categoryValue',
                                   'name': 'bpmn:categoryValue',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:CategoryValue'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['RootElement']},
           {'isAbstract': True,
            'name': 'Artifact',
            'superClass': ['BaseElement']},
           {'name': 'CategoryValue',
            'properties': [{'isMany': True,
                            'isReference': True,
                            'isVirtual': True,
                            'name': 'bpmn:categorizedFlowElements',
                            'ns': {'localName': 'categorizedFlowElements',
                                   'name': 'bpmn:categorizedFlowElements',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FlowElement'},
                           {'isAttr': True,
                            'name': 'bpmn:value',
                            'ns': {'localName': 'value',
                                   'name': 'bpmn:value',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'isAbstract': True,
            'name': 'Activity',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isForCompensation',
                            'ns': {'localName': 'isForCompensation',
                                   'name': 'bpmn:isForCompensation',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:default',
                            'ns': {'localName': 'default',
                                   'name': 'bpmn:default',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:SequenceFlow'},
                           {'name': 'bpmn:ioSpecification',
                            'ns': {'localName': 'ioSpecification',
                                   'name': 'bpmn:ioSpecification',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:InputOutputSpecification',
                            'xml': {'serialize': 'property'}},
                           {'isMany': True,
                            'isReference': True,
                            'name': 'bpmn:boundaryEventRefs',
                            'ns': {'localName': 'boundaryEventRefs',
                                   'name': 'bpmn:boundaryEventRefs',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:BoundaryEvent'},
                           {'isMany': True,
                            'name': 'bpmn:properties',
                            'ns': {'localName': 'properties',
                                   'name': 'bpmn:properties',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Property'},
                           {'isMany': True,
                            'name': 'bpmn:dataInputAssociations',
                            'ns': {'localName': 'dataInputAssociations',
                                   'name': 'bpmn:dataInputAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInputAssociation'},
                           {'isMany': True,
                            'name': 'bpmn:dataOutputAssociations',
                            'ns': {'localName': 'dataOutputAssociations',
                                   'name': 'bpmn:dataOutputAssociations',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutputAssociation'},
                           {'default': 1,
                            'isAttr': True,
                            'name': 'bpmn:startQuantity',
                            'ns': {'localName': 'startQuantity',
                                   'name': 'bpmn:startQuantity',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'},
                           {'isMany': True,
                            'name': 'bpmn:resources',
                            'ns': {'localName': 'resources',
                                   'name': 'bpmn:resources',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceRole'},
                           {'default': 1,
                            'isAttr': True,
                            'name': 'bpmn:completionQuantity',
                            'ns': {'localName': 'completionQuantity',
                                   'name': 'bpmn:completionQuantity',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'},
                           {'name': 'bpmn:loopCharacteristics',
                            'ns': {'localName': 'loopCharacteristics',
                                   'name': 'bpmn:loopCharacteristics',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:LoopCharacteristics'}],
            'superClass': ['FlowNode']},
           {'name': 'ServiceTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:operationRef',
                            'ns': {'localName': 'operationRef',
                                   'name': 'bpmn:operationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'}],
            'superClass': ['Task']},
           {'name': 'SubProcess',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:triggeredByEvent',
                            'ns': {'localName': 'triggeredByEvent',
                                   'name': 'bpmn:triggeredByEvent',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isMany': True,
                            'name': 'bpmn:artifacts',
                            'ns': {'localName': 'artifacts',
                                   'name': 'bpmn:artifacts',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Artifact'}],
            'superClass': ['Activity', 'FlowElementsContainer',
                           'InteractionNode']},
           {'isAbstract': True,
            'name': 'LoopCharacteristics',
            'superClass': ['BaseElement']},
           {'name': 'MultiInstanceLoopCharacteristics',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:isSequential',
                            'ns': {'localName': 'isSequential',
                                   'name': 'bpmn:isSequential',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'default': 'All',
                            'isAttr': True,
                            'name': 'bpmn:behavior',
                            'ns': {'localName': 'behavior',
                                   'name': 'bpmn:behavior',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:MultiInstanceBehavior'},
                           {'name': 'bpmn:loopCardinality',
                            'ns': {'localName': 'loopCardinality',
                                   'name': 'bpmn:loopCardinality',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isReference': True,
                            'name': 'bpmn:loopDataInputRef',
                            'ns': {'localName': 'loopDataInputRef',
                                   'name': 'bpmn:loopDataInputRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemAwareElement'},
                           {'isReference': True,
                            'name': 'bpmn:loopDataOutputRef',
                            'ns': {'localName': 'loopDataOutputRef',
                                   'name': 'bpmn:loopDataOutputRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ItemAwareElement'},
                           {'name': 'bpmn:inputDataItem',
                            'ns': {'localName': 'inputDataItem',
                                   'name': 'bpmn:inputDataItem',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataInput',
                            'xml': {'serialize': 'property'}},
                           {'name': 'bpmn:outputDataItem',
                            'ns': {'localName': 'outputDataItem',
                                   'name': 'bpmn:outputDataItem',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:DataOutput',
                            'xml': {'serialize': 'property'}},
                           {'isMany': True,
                            'name': 'bpmn:complexBehaviorDefinition',
                            'ns': {'localName': 'complexBehaviorDefinition',
                                   'name': 'bpmn:complexBehaviorDefinition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ComplexBehaviorDefinition'},
                           {'name': 'bpmn:completionCondition',
                            'ns': {'localName': 'completionCondition',
                                   'name': 'bpmn:completionCondition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:oneBehaviorEventRef',
                            'ns': {'localName': 'oneBehaviorEventRef',
                                   'name': 'bpmn:oneBehaviorEventRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:noneBehaviorEventRef',
                            'ns': {'localName': 'noneBehaviorEventRef',
                                   'name': 'bpmn:noneBehaviorEventRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:EventDefinition'}],
            'superClass': ['LoopCharacteristics']},
           {'name': 'StandardLoopCharacteristics',
            'properties': [{'default': False,
                            'isAttr': True,
                            'name': 'bpmn:testBefore',
                            'ns': {'localName': 'testBefore',
                                   'name': 'bpmn:testBefore',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'name': 'bpmn:loopCondition',
                            'ns': {'localName': 'loopCondition',
                                   'name': 'bpmn:loopCondition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'name': 'bpmn:loopMaximum',
                            'ns': {'localName': 'loopMaximum',
                                   'name': 'bpmn:loopMaximum',
                                   'prefix': 'bpmn'},
                            'type': 'Integer'}],
            'superClass': ['LoopCharacteristics']},
           {'name': 'CallActivity',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:calledElement',
                            'ns': {'localName': 'calledElement',
                                   'name': 'bpmn:calledElement',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['Activity']},
           {'name': 'Task', 'superClass': ['Activity', 'InteractionNode']},
           {'name': 'SendTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:operationRef',
                            'ns': {'localName': 'operationRef',
                                   'name': 'bpmn:operationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:messageRef',
                            'ns': {'localName': 'messageRef',
                                   'name': 'bpmn:messageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'}],
            'superClass': ['Task']},
           {'name': 'ReceiveTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': False,
                            'isAttr': True,
                            'name': 'bpmn:instantiate',
                            'ns': {'localName': 'instantiate',
                                   'name': 'bpmn:instantiate',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:operationRef',
                            'ns': {'localName': 'operationRef',
                                   'name': 'bpmn:operationRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Operation'},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:messageRef',
                            'ns': {'localName': 'messageRef',
                                   'name': 'bpmn:messageRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Message'}],
            'superClass': ['Task']},
           {'name': 'ScriptTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:scriptFormat',
                            'ns': {'localName': 'scriptFormat',
                                   'name': 'bpmn:scriptFormat',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'name': 'bpmn:script',
                            'ns': {'localName': 'script',
                                   'name': 'bpmn:script',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['Task']},
           {'name': 'BusinessRuleTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['Task']},
           {'name': 'AdHocSubProcess',
            'properties': [{'name': 'bpmn:completionCondition',
                            'ns': {'localName': 'completionCondition',
                                   'name': 'bpmn:completionCondition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'name': 'bpmn:ordering',
                            'ns': {'localName': 'ordering',
                                   'name': 'bpmn:ordering',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:AdHocOrdering'},
                           {'default': True,
                            'isAttr': True,
                            'name': 'bpmn:cancelRemainingInstances',
                            'ns': {'localName': 'cancelRemainingInstances',
                                   'name': 'bpmn:cancelRemainingInstances',
                                   'prefix': 'bpmn'},
                            'type': 'Boolean'}],
            'superClass': ['SubProcess']},
           {'name': 'Transaction',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:protocol',
                            'ns': {'localName': 'protocol',
                                   'name': 'bpmn:protocol',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:method',
                            'ns': {'localName': 'method',
                                   'name': 'bpmn:method',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['SubProcess']},
           {'name': 'GlobalScriptTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:scriptLanguage',
                            'ns': {'localName': 'scriptLanguage',
                                   'name': 'bpmn:scriptLanguage',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:script',
                            'ns': {'localName': 'script',
                                   'name': 'bpmn:script',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['GlobalTask']},
           {'name': 'GlobalBusinessRuleTask',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:implementation',
                            'ns': {'localName': 'implementation',
                                   'name': 'bpmn:implementation',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['GlobalTask']},
           {'name': 'ComplexBehaviorDefinition',
            'properties': [{'name': 'bpmn:condition',
                            'ns': {'localName': 'condition',
                                   'name': 'bpmn:condition',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:FormalExpression'},
                           {'name': 'bpmn:event',
                            'ns': {'localName': 'event',
                                   'name': 'bpmn:event',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ImplicitThrowEvent'}],
            'superClass': ['BaseElement']},
           {'name': 'ResourceRole',
            'properties': [{'isReference': True,
                            'name': 'bpmn:resourceRef',
                            'ns': {'localName': 'resourceRef',
                                   'name': 'bpmn:resourceRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Resource'},
                           {'isMany': True,
                            'name': 'bpmn:resourceParameterBindings',
                            'ns': {'localName': 'resourceParameterBindings',
                                   'name': 'bpmn:resourceParameterBindings',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceParameterBinding'},
                           {'name': 'bpmn:resourceAssignmentExpression',
                            'ns': {'localName': 'resourceAssignmentExpression',
                                   'name': 'bpmn:resourceAssignmentExpression',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceAssignmentExpression'},
                           {'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']},
           {'name': 'ResourceParameterBinding',
            'properties': [{'name': 'bpmn:expression',
                            'ns': {'localName': 'expression',
                                   'name': 'bpmn:expression',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}},
                           {'isAttr': True,
                            'isReference': True,
                            'name': 'bpmn:parameterRef',
                            'ns': {'localName': 'parameterRef',
                                   'name': 'bpmn:parameterRef',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:ResourceParameter'}],
            'superClass': ['BaseElement']},
           {'name': 'ResourceAssignmentExpression',
            'properties': [{'name': 'bpmn:expression',
                            'ns': {'localName': 'expression',
                                   'name': 'bpmn:expression',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Expression',
                            'xml': {'serialize': 'xsi:type'}}],
            'superClass': ['BaseElement']},
           {'name': 'Import',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:importType',
                            'ns': {'localName': 'importType',
                                   'name': 'bpmn:importType',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:location',
                            'ns': {'localName': 'location',
                                   'name': 'bpmn:location',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:namespace',
                            'ns': {'localName': 'namespace',
                                   'name': 'bpmn:namespace',
                                   'prefix': 'bpmn'},
                            'type': 'String'}]},
           {'name': 'Definitions',
            'properties': [{'isAttr': True,
                            'name': 'bpmn:name',
                            'ns': {'localName': 'name',
                                   'name': 'bpmn:name',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isAttr': True,
                            'name': 'bpmn:targetNamespace',
                            'ns': {'localName': 'targetNamespace',
                                   'name': 'bpmn:targetNamespace',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': 'http://www.w3.org/1999/XPath',
                            'isAttr': True,
                            'name': 'bpmn:expressionLanguage',
                            'ns': {'localName': 'expressionLanguage',
                                   'name': 'bpmn:expressionLanguage',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'default': 'http://www.w3.org/2001/XMLSchema',
                            'isAttr': True,
                            'name': 'bpmn:typeLanguage',
                            'ns': {'localName': 'typeLanguage',
                                   'name': 'bpmn:typeLanguage',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:imports',
                            'ns': {'localName': 'imports',
                                   'name': 'bpmn:imports',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Import'},
                           {'isMany': True,
                            'name': 'bpmn:extensions',
                            'ns': {'localName': 'extensions',
                                   'name': 'bpmn:extensions',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Extension'},
                           {'isMany': True,
                            'name': 'bpmn:rootElements',
                            'ns': {'localName': 'rootElements',
                                   'name': 'bpmn:rootElements',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:RootElement'},
                           {'isMany': True,
                            'name': 'bpmn:diagrams',
                            'ns': {'localName': 'diagrams',
                                   'name': 'bpmn:diagrams',
                                   'prefix': 'bpmn'},
                            'type': 'bpmndi:BPMNDiagram'},
                           {'isAttr': True,
                            'name': 'bpmn:exporter',
                            'ns': {'localName': 'exporter',
                                   'name': 'bpmn:exporter',
                                   'prefix': 'bpmn'},
                            'type': 'String'},
                           {'isMany': True,
                            'name': 'bpmn:relationships',
                            'ns': {'localName': 'relationships',
                                   'name': 'bpmn:relationships',
                                   'prefix': 'bpmn'},
                            'type': 'bpmn:Relationship'},
                           {'isAttr': True,
                            'name': 'bpmn:exporterVersion',
                            'ns': {'localName': 'exporterVersion',
                                   'name': 'bpmn:exporterVersion',
                                   'prefix': 'bpmn'},
                            'type': 'String'}],
            'superClass': ['BaseElement']}],
 'uri': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
 'xml': {'tagAlias': 'lowerCase', 'typePrefix': 't'}}

registry = cmof.Registry([
    ActivationCondition,
    Activity,
    AdHocOrdering,
    AdHocSubProcess,
    Artifact,
    Artifacts,
    Assignment,
    Association,
    AssociationDirection,
    Auditing,
    BaseElement,
    Body,
    BoundaryEvent,
    BoundaryEventRefs,
    BusinessRuleTask,
    CallActivity,
    CallChoreography,
    CallConversation,
    CallableElement,
    CancelEventDefinition,
    CatchEvent,
    CategorizedFlowElements,
    Category,
    CategoryValue,
    CategoryValueRef,
    ChildLaneSet,
    Choreography,
    ChoreographyActivity,
    ChoreographyLoopType,
    ChoreographyRef,
    ChoreographyTask,
    Collaboration,
    CompensateEventDefinition,
    CompletionCondition,
    ComplexBehaviorDefinition,
    ComplexGateway,
    Condition,
    ConditionExpression,
    ConditionalEventDefinition,
    Conversation,
    ConversationAssociation,
    ConversationAssociations,
    ConversationLink,
    ConversationLinks,
    ConversationNode,
    ConversationNodes,
    Conversations,
    CorrelationKey,
    CorrelationKeys,
    CorrelationProperty,
    CorrelationPropertyBinding,
    CorrelationPropertyRef,
    CorrelationPropertyRetrievalExpression,
    CorrelationSubscription,
    CorrelationSubscriptions,
    DataAssociation,
    DataInput,
    DataInputAssociation,
    DataInputAssociations,
    DataInputRefs,
    DataInputs,
    DataObject,
    DataObjectReference,
    DataOutput,
    DataOutputAssociation,
    DataOutputAssociations,
    DataOutputRefs,
    DataOutputs,
    DataPath,
    DataState,
    DataStore,
    DataStoreReference,
    Definitions,
    Diagrams,
    Documentation,
    EndEvent,
    EndPoint,
    EndPointRefs,
    Error,
    ErrorEventDefinition,
    ErrorRef,
    Escalation,
    EscalationEventDefinition,
    Event,
    EventBasedGateway,
    EventBasedGatewayType,
    EventDefinition,
    EventDefinitionRef,
    EventDefinitions,
    ExclusiveGateway,
    Expression,
    Extension,
    ExtensionAttributeDefinition,
    ExtensionAttributeDefinitions,
    ExtensionDefinition,
    ExtensionDefinitions,
    ExtensionElements,
    Extensions,
    FlowElement,
    FlowElements,
    FlowElementsContainer,
    FlowNode,
    FlowNodeRef,
    FormalExpression,
    From,
    Gateway,
    GatewayDirection,
    GlobalBusinessRuleTask,
    GlobalChoreographyTask,
    GlobalConversation,
    GlobalManualTask,
    GlobalScriptTask,
    GlobalTask,
    GlobalUserTask,
    Group,
    HumanPerformer,
    ImplicitThrowEvent,
    Import,
    Imports,
    InMessageRef,
    InclusiveGateway,
    Incoming,
    IncomingConversationLinks,
    InputDataItem,
    InputOutputBinding,
    InputOutputSpecification,
    InputSet,
    InputSetRef,
    InputSetRefs,
    InputSetWithOptional,
    InputSetWithWhileExecuting,
    InputSets,
    InteractionNode,
    Interface,
    InterfaceRef,
    IntermediateCatchEvent,
    IntermediateThrowEvent,
    IoBinding,
    IoSpecification,
    ItemAwareElement,
    ItemDefinition,
    ItemKind,
    Lane,
    LaneSet,
    LaneSets,
    Lanes,
    LinkEventDefinition,
    LoopCardinality,
    LoopCharacteristics,
    LoopCondition,
    LoopDataInputRef,
    LoopDataOutputRef,
    ManualTask,
    Message,
    MessageEventDefinition,
    MessageFlow,
    MessageFlowAssociation,
    MessageFlowAssociations,
    MessageFlowRef,
    MessageFlowRefs,
    MessageFlows,
    MessagePath,
    Monitoring,
    MultiInstanceBehavior,
    MultiInstanceLoopCharacteristics,
    Operation,
    Operations,
    OptionalInputRefs,
    OptionalOutputRefs,
    OutMessageRef,
    Outgoing,
    OutgoingConversationLinks,
    OutputDataItem,
    OutputSet,
    OutputSetRef,
    OutputSetRefs,
    OutputSetWithOptional,
    OutputSetWithWhileExecuting,
    OutputSets,
    ParallelGateway,
    Participant,
    ParticipantAssociation,
    ParticipantAssociations,
    ParticipantMultiplicity,
    ParticipantRef,
    Participants,
    PartitionElement,
    PartnerEntity,
    PartnerRole,
    Performer,
    PotentialOwner,
    Process,
    ProcessType,
    Properties,
    Property,
    ReceiveTask,
    Relationship,
    RelationshipDirection,
    Relationships,
    Rendering,
    Renderings,
    Resource,
    ResourceAssignmentExpression,
    ResourceParameter,
    ResourceParameterBinding,
    ResourceParameterBindings,
    ResourceParameters,
    ResourceRef,
    ResourceRole,
    Resources,
    RootElement,
    RootElements,
    Script,
    ScriptTask,
    SendTask,
    SequenceFlow,
    ServiceTask,
    Signal,
    SignalEventDefinition,
    Source,
    SourceRef,
    StandardLoopCharacteristics,
    StartEvent,
    SubChoreography,
    SubConversation,
    SubProcess,
    SupportedInterfaceRef,
    Supports,
    Target,
    TargetRef,
    Task,
    TerminateEventDefinition,
    Text,
    TextAnnotation,
    ThrowEvent,
    TimeCycle,
    TimeDate,
    TimeDuration,
    TimerEventDefinition,
    To,
    Transaction,
    Transformation,
    UserTask,
    Values,
    WhileExecutingInputRefs,
    WhileExecutingOutputRefs,
], package_map = {'bpmn': PACKAGE_METADATA})
