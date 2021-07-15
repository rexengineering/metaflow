import asyncio
import logging

from os import path
from graphql import build_ast_schema, parse

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from httpx import AsyncClient

from . import queries
from . import entities

logger = logging.getLogger(__name__)

schema_files = [
    'mutations.graphql',
    'query.graphql',
]

basepath = path.dirname(__file__)

schemas = []
for schema in schema_files:
    filepath = path.abspath(path.join(basepath, 'callback/schema', schema))
    with open(filepath) as f:
        schemas.append(f.read())

schema = build_ast_schema(parse('\n\n'.join(schemas)))

class PrismApiClient:
    @classmethod
    def get_transport(cls, url):
        transport = AIOHTTPTransport(
            url = url
        )
        return transport
    
    @classmethod
    async def notify_task_started(cls, url:str, iid:str, tid:str):
        """
        notify PRISM that the given task has started
        """
        async with Client(
            transport=cls.get_transport(url),
            schema=schema,
        ) as session:
            query = gql(queries.TASK_START_MUTATION)
            params = {
                'startTaskInput' : entities.StartTaskInput(
                    iid=iid,
                    tid=tid,
                ).dict(),
            }

            result = await session.execute(query, variable_values=params)
            logger.info(result)

            payload = entities.StartTaskPayload(
                **result['task']['start']
            )
            logger.info(payload)
            return payload.status
            
    @classmethod
    async def complete_workflow(cls, url:str, iid:str):
        async with Client(
            transport=cls.get_transport(url),
            schema=schema,
        ) as session:
            query = gql(queries.WORKFLOW_COMPLETE_MUTATION)
            params = {
                'completeWorkflowInput' : entities.CompleteWorkflowInput(
                    iid=iid,
                ).dict(),
            }

            result = await session.execute(query, variable_values=params)
            logger.info(result)

            payload = entities.CompleteWorkflowPayload(
                **result['workflow']['complete']
            )
            logger.info(payload)
            return payload.status

            