# Path Templating

Test suite to test the path templating widget.

## Build test containers

```python build.py```

## (Optional) Run Test container
Just to get a feel for what the app does.

In one shell:
```docker run -p 5000:5000 favorite-food```

In another shell:
```->curl -d '{}' localhost:5000/coworker/Gary/favorite-food
{"coworker_name":"Gary","favorite_food":"Tumble 22"}

->curl -d '{}' localhost:5000/coworker/Andrew/favorite-food
{"coworker_name":"Andrew","favorite_food":"Chick Fil A"}

```

## Run the Workflow
```
flowctl apply path_templating.bpmn
# Wait for it to come up

kubectl get virtualservice -ndefault | grep start
# Note the name of this virtualservice

kubectl -ndefault get virtualservice <<virtualservice_from_above>> -o yaml
# This should show you the spec. Look for the http.match.uri.prefix, for example '/start-287383a9'

curl -d '{"coworker": "Gary"}' -H "content-type: application/json" localhost/start-287383a9
```

Right now, the workflow instance _does_ actually complete...but doesn't do what we want:
```
"process-1tbxrdw-287383a9-fa96868cb3e711eb91c65ad15ec22e12": {
    "content_type": "application/json",
    "end_event": "end",
    "parent": "process-1tbxrdw-287383a9",
    "result": "{\"coworker\": \"{coworker}\",\"food\": \"McDonald's\"}",
    "state": "COMPLETED"
  }
```

What we want to see for the same command above:

```"process-1tbxrdw-287383a9-fa96868cb3e711eb91c65ad15ec22e12": {
    "content_type": "application/json",
    "end_event": "end",
    "parent": "process-1tbxrdw-287383a9",
    "result": "{\"coworker\": \"Gary\",\"food\": \"Tumble 22\"}",
    "state": "COMPLETED"
  }
```
