'''I believe this file is no longer used, except for the definition of the Upstream tuple.
This file contains code to define the Lua Filters and Envoy Configurations for the
Docker Stack deployment.
'''

from collections import namedtuple
import logging
import tempfile

import yaml


Upstream = namedtuple('Upstream', ['name', 'host', 'port'])


def gen_address(address, port):
    return {
        'socket_address' : {
            'address' : address,
            'port_value' : port,
        },
    }


def gen_envoy_lua(upstreams=None):
    if upstreams is None:
        upstreams = []
    result = '''
function headers_obj_to_table(headers)
    local headers_table = {{}}
    for key, value in pairs(headers) do
        headers_table[key] = value
    end
    return headers_table
end
function table_update(headers, additional_headers)
    if additional_headers ~= nil then
        for key, value in pairs(additional_headers) do
            headers[key] = value
        end
    end
    return headers
end
function envoy_on_request(request_handle)
    local request_headers = request_handle:headers()
    local request_headers_table = headers_obj_to_table(request_headers)
    local flow_id = request_headers:get("x-flow-id")
    if flow_id ~= nil then
        request_handle:logInfo("Handling flow ID = " .. flow_id)
        local size = request_handle:body():length()
        local headers, body = request_handle:httpCall(
            "local_service",
            request_headers_table,
            request_handle:body():getBytes(0, size),
            30000,
            false
        )
        local headers_table = headers_obj_to_table(headers)
        headers_table[':status'] = nil
        headers_table['server'] = nil
        table_update(headers_table, {{
            [":method"] = "POST",
            [":path"] = "/",
            [":authority"] = "",
            ["x-flow-id"] = flow_id
        }}){}
        request_handle:respond({{[":status"] = "200"}}, nil)
    end
end
'''.format(''.join([f'''
        request_handle:httpCall(
            "{upstream.name}", headers_table, body, 500, true)'''
    for upstream in upstreams]))
    logging.debug(f'Generated Lua code:\n{result}')
    return result

def dummy_gen_envoy_lua(*args, **kws):
    return '''
function envoy_on_request(request_handle)
    request_handle:logInfo("In envoy_on_request()...")
end

function envoy_on_response(response_handle)
    response_handle:logInfo("In envoy_on_response()...")
end
'''


def gen_envoy_config(service_name='localhost', upstreams=None, port=5000, *args, **kws):
    if upstreams is None:
        upstreams = []
    return {
        'static_resources' : {
            'listeners' : [
                {
                    'name' : 'main',
                    'address' : gen_address('0.0.0.0', port),
                    'filter_chains' : [
                        {
                            'filters' : [
                                {
                                    'name' : 'envoy.filters.network.http_connection_manager',
                                    'typed_config' : {
                                        '@type' : 'type.googleapis.com/envoy.config.filter.network.http_connection_manager.v2.HttpConnectionManager',
                                        'stat_prefix' : 'ingress_http',
                                        'codec_type' : 'auto',
                                        'route_config' : {
                                            'name' : 'local_route',
                                            'virtual_hosts' : [
                                                {
                                                    'name' : 'local_service',
                                                    'domains' : ['*'],
                                                    'routes' : [
                                                        {
                                                            'match' : {
                                                                'prefix' : '/',
                                                                },
                                                            'route' : {
                                                                'cluster' : 'local_service',
                                                            },
                                                        },
                                                    ],
                                                },
                                            ],
                                        },
                                        'http_filters' : [
                                            {
                                                'name' : 'envoy.filters.http.lua',
                                                'typed_config' : {
                                                    '@type' : 'type.googleapis.com/envoy.config.filter.http.lua.v2.Lua',
                                                    'inline_code' : gen_envoy_lua(upstreams),
                                                }
                                            },
                                            {
                                                'name' : 'envoy.filters.http.router',
                                                'typed_config' : {},
                                            },
                                        ],
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
            'clusters' : [
                {
                    'name' : 'local_service',
                    'connect_timeout' : '0.5s',
                    'type' : 'strict_dns',
                    'lb_policy' : 'round_robin',
                    'load_assignment' : {
                        'cluster_name' : 'local_service',
                        'endpoints' : [
                            {
                                'lb_endpoints' : [
                                    {
                                        'endpoint' : {
                                            'address' : gen_address(service_name, port),
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                },
            ] + [
                {
                    'name' : upstream.name,
                    'connect_timeout' : '0.5s',
                    'type' : 'strict_dns',
                    'lb_policy' : 'round_robin',
                    'load_assignment' : {
                        'cluster_name' : upstream.name,
                        'endpoints' : [
                            {
                                'lb_endpoints' : [
                                    {
                                        'endpoint' : {
                                            'address' : gen_address(upstream.host, upstream.port),
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                }
                for upstream in upstreams
            ],
        },
        'admin' : {
            'access_log_path' : '/dev/null',
            'address' : gen_address('0.0.0.0', port + 1),
        },
    }


def get_envoy_config(service_name='localhost', upstreams=None, port=5000, *args, **kws):
    if upstreams is None:
        upstreams = []
    with tempfile.NamedTemporaryFile(delete=False, dir='/tmp') as temp:
        yaml.safe_dump(gen_envoy_config(service_name, upstreams, port, *args,
                       **kws), temp, encoding='utf-8')
        return temp.name
