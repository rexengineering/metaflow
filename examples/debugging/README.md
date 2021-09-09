# REXFlow Debugging Examples

## Building and using `debuggee`

The provided Dockerfile in this directory builds the `debuggee` Flask service.
Example:

```shell
$ docker build -t debuggee .
$ flowctl apply the_bugs.bpmn
```

```
curl -v -X POST -d '{"poison": "wait_a_while"}' http://localhost:5000/
curl -v http://localhost:5000/fail_miserably
curl -v http://localhost:5000/fail_miserably
curl -v http://localhost:5000/always500
curl -v http://localhost:5000/fail_miserably
curl -v -d '{"poison": ["wait_a_while"]}' http://localhost:5000/
curl -v -d '{"poison": ["wait_a_while", "fail_miserably"]}' http://localhost:5000/
curl -v -d '{"poison": ["wait_a_while"], "cb": "http://localhost:5000/"}' http://localhost:5000/async
```

