'''Defines utilities for reliable workflows. Specifically, utility functions are exposed
that return k8s specs for the python services that aid the Envoy Proxy in sending messages
to Kafka for Reliable Workflows.

A quick note on architecture:
Each BPMNComponent in a reliable wf has a `kafka_topic` attribute, which is the Kafka
Topic on which the component listens. In a reliable wf, 
'''
from collections import namedtuple

from .k8s_utils import (
    create_deployment,
    create_service,
    create_serviceaccount,
    create_rexflow_ingress_vs,
    create_deployment_affinity,
)

from .bpmn_util import (
    BPMNComponent,
    HealthProperties,
)

from .constants import to_valid_k8s_name

from .config import (
    ETCD_HOST,
    KAFKA_HOST,
    THROW_IMAGE,
    THROW_LISTEN_PORT,
    CATCH_IMAGE,
    CATCH_LISTEN_PORT,
    INSTANCE_FAIL_ENDPOINT,
)

DEFAULT_TOTAL_ATTEMPTS = '2'


def create_reliable_wf_catcher(
        service_name, namespace, wf_id, kafka_topic, forward_url, task_id, dest_service_name):
    k8s_objects = []
    env_config = [
        {
            "name": 'KAFKA_HOST',
            "value": KAFKA_HOST,
        },
        {
            "name": "REXFLOW_CATCH_START_FUNCTION",
            "value": "CATCH",
        },
        {
            "name": "WF_ID",
            "value": wf_id,
        },
        {
            "name": "TOTAL_ATTEMPTS",
            "value": DEFAULT_TOTAL_ATTEMPTS,
        },
        {
            "name": "FORWARD_URL",
            "value": forward_url,
        },
        {
            "name": "FORWARD_TASK_ID",
            "value": task_id,
        },
        {
            "name": "KAFKA_GROUP_ID",
            "value": service_name,
        },
        {
            "name": "KAFKA_TOPIC",
            "value": kafka_topic,
        }
    ]
    k8s_objects.append(create_serviceaccount(namespace, service_name))
    k8s_objects.append(create_service(namespace, service_name, CATCH_LISTEN_PORT))
    deployment = create_deployment(
        namespace,
        service_name,
        CATCH_IMAGE,
        CATCH_LISTEN_PORT,
        env_config,
        kafka_access=True,
        etcd_access=True,
    )
    deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
        service_name=dest_service_name,  # Want to be on same node as service we call
        anti_service_name=service_name,  # Don't need more than one catcher per node
    )
    k8s_objects.append(deployment)

    return k8s_objects


def create_reliable_wf_thrower(service_name, namespace, kafka_topic, source_service_name):
    k8s_objects = []
    env_config = [
        {
            "name": "KAFKA_TOPIC",
            "value": kafka_topic,
        },
        {
            "name": "FORWARD_URL",
            "value": None,
        },
        {
            "name": "TOTAL_ATTEMPTS",
            "value": DEFAULT_TOTAL_ATTEMPTS,
        },
        {
            "name": "FORWARD_TASK_ID",
            "value": '',
        },
    ]

    k8s_objects.append(create_serviceaccount(namespace, service_name))
    k8s_objects.append(create_service(namespace, service_name, THROW_LISTEN_PORT))
    deployment = create_deployment(
        namespace,
        service_name,
        THROW_IMAGE,
        THROW_LISTEN_PORT,
        env_config,
        kafka_access=True,
    )
    deployment['spec']['template']['spec']['affinity'] = create_deployment_affinity(
        service_name=source_service_name,  # schedule thrower on same node as source service
        anti_service_name=service_name,  # don't need two throwers on same node
    )
    k8s_objects.append(deployment)
    return k8s_objects


TransportCallDetails = namedtuple(
    'TransportCallDetails',
    ['k8s_specs', 'envoy_host', 'port', 'path', 'method', 'total_attempts', 'kafka_topic'],
)


def create_kafka_transport(
        from_component: BPMNComponent, to_component: BPMNComponent) -> TransportCallDetails:
    '''Creates k8s specs for reliable transport via kafka between two BPMNComponents. There are
    two things that need to be created:
    1. The helper service that accepts rpc calls from the `from_component` and publishes it to
       the designated Kafka topic.
    2. The helper service that listens to the designated kafka topic, and sends rpc calls to the
       `to_component` service.

    The helper components are deployed into the namespace that the Workflow is deployed into,
    regardless of whether either to_component or from_component is in a different, preexisting
    namespace.

    The service names are:
    1. f'throw-{from_component.name}-to-{to_component.name}'
    2. f'catch-{from_component.name}-to-{to_component.name}'
    
    The kafka topic name is:
       f'reliable-transport_{from_component.name}_to_{to_component.name}_{worklow_id}'
    where workflow_id is the ID of the parent workflow.
    '''
    throw_service_name = to_valid_k8s_name(f'throw-{from_component.name}-to-{to_component.name}')
    catch_service_name = to_valid_k8s_name(f'catch-{from_component.name}-to-{to_component.name}')

    # Take my word for it, this will match the 
    kafka_topic_name = f'rexflow-transport_{from_component.workflow_properties.id}_'
    kafka_topic_name += f'{from_component.name}_to_{to_component.name}'

    wf_id = from_component.workflow_properties.id
    assert wf_id == to_component.workflow_properties.id, \
        "Kafka Reliable Transport called for BPMN Components of different Workflow ID's!!!"

    namespace = from_component.workflow_properties.namespace
    assert namespace == to_component.workflow_properties.namespace, \
        "Global namespace should match within same wf."

    k8s_specs = []

    k8s_specs.extend(create_reliable_wf_catcher(
        catch_service_name,
        namespace,
        wf_id,
        kafka_topic_name,
        to_component.k8s_url,
        to_component.id,
        to_component.service_name,
    ))

    k8s_specs.extend(create_reliable_wf_thrower(
        throw_service_name,
        namespace,
        kafka_topic_name,
        from_component.service_name,
    ))

    # Mark the kafka topic so it gets created
    from_component._kafka_topics.append(kafka_topic_name)

    return TransportCallDetails(
        k8s_specs,
        f'{throw_service_name}.{namespace}.svc.cluster.local',
        THROW_LISTEN_PORT,
        '/',
        'POST',
        DEFAULT_TOTAL_ATTEMPTS,
        kafka_topic_name,
    )


