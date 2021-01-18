# Parallel Gateway

Must be deployed with following environment variables:

REXFLOW_PGW_TYPE              'splitter' or 'combiner'
REXFLOW_PGW_INCOMING_COUNT    number of incoming connections
REXFLOW_PGW_FORWARD_URL       combiner's outgoing URL
REXFLOW_PGW_FORWARD_ID        combiner's outgoing ID
REXFLOW_PGW_FORWARD_URLS      list (json string) of splitter's outgoing URL
REXFLOW_PGW_FORWARD_IDS       list (json string) of splitter's outgoing IDs
