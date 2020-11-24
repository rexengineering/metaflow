# Exclusive Gateway

Must be deployed with following environment variables:

`REXFLOW_XGW_JSONPATH`: path of the json object to inspect
`REXFLOW_XGW_OPERATOR`: one of `==`, `<`, `>`
`REXFLOW_XGW_COMPARISON_VALUE`: value to compare input_json[jsonpath] to.
`REXFLOW_XGW_TRUE_URL`: url to send incoming data to in case comparison is "true"
`REXFLOW_XGW_FALSE_URL`: url to send incoming data to in case comparison is "false"