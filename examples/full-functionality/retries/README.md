# Retries

This example demonstrates Retries and "resuming" a failed WF Instance. In `retry-demo.bpmn`, the second step of the Workflow is configured to return a `500` 40% of the time and to succeed the rest of the time.

We have also configured the WF Engine to attempt the Unreliable Sauce step 2 times before giving up.

```
python -m flowctl apply retry-demo.bpmn

# Run this in another shell, after the Deployment is `RUNNING`
kubectl -nretry-demo logs -f $(kubectl -n retry-demo get po | grep unreliable | cut -d ' ' -f1) -c unreliable-sauce

# Do this a few times
python -m flowctl run retry-demo '{}'
```

After running a few WF Instances, doing a `python -m flowctl ps` should show some instances as `COMPLETED` and some as `ERROR`. To try an `ERROR` instance again, please do:

```
python -m flowctl start -k INSTANCE <<Failed WF Instance ID>>
```
