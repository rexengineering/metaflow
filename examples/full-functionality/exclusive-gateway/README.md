# Exclusive (conditional) Gateway

```
python -m flowctl apply conditional.bpmn
python -m flowctl run conditional '{}'
```

Demonstrates trivial example of the Conditional Gateway. The `collect` container (see `examples/underpants/src/server.py`) has been modified to randomly return either:

```
{"Underpants:" "collected"}
```

OR

```
{"Underpants:" "Not Collected ):"}
```

The workflow in `conditional.bpmn` is the same as the normal `examples/istio/istio-underpants.bpmn` except that we only apply sauce and profit if we successfully collect underpants.