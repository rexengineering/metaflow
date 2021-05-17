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
    filepath = path.abspath(path.join(basepath, 'schema', schema))
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
    async def start_task(cls, url:str, iid:str, tid:str):
        async with Client(
            transport=cls.get_transport(url),
            schema=schema,
        ) as session:
            query = gql(queries.START_TASK_MUTATION)
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
            query = gql(queries.COMPLETE_WORKFLOW_MUTATION)
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

            