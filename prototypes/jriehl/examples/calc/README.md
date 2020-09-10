Running the Example
===================

* Setup operating environment per the [top-level REAMDME](../../README.md).
* Build a Docker image for the test server.
    ```console
    % docker build -t calc_2_x_to_2 .
    ```
* Deploy a workflow using `flowctl`, passing the example's BPMN file as an argument to the `apply` subcommand.
    ```console
    $ python -m flowctl apply calcprocess.bpmn
    2020-09-10 10:36:18,559|flowctl|INFO|apply_action.py:59|Got response: 0, "Ok", {"CalcProcess": "CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122"}
    ```
* Verify the workflow has deployed using `flowctl ps`, paying particular attention
  to the state of the deployment, waiting for the `RUNNING` state.
    ```console
    % watch python -m flowctl ps --kind DEPLOYMENT
    % python -m flowctl ps --kind DEPLOYMENT
    2020-09-10 10:36:58,744|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {"CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122": {"state": "RUNNING"}}
    ```
* (As a convenience, create a shorthand variable to hold the deployment ID.)
    ```console
    % WF_PROC=CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122
    ```
* Run a worflow instance using `flowctl run`.
    ```console
    % python -m flowctl run $WF_PROC 1 2 3
    2020-09-10 10:37:16,798|flowctl|INFO|run_action.py:35|Got response: 0, "Ok", {"CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122": "flow-8188a784f37b11ea9ac2acde48001122"}
    ```
* Wait for results from the workflow instance using `flowctl ps`.
    ```console
    % python -m flowctl ps
    2020-09-10 10:37:36,654|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {"flow-8188a784f37b11ea9ac2acde48001122": {"result": "[2.0,8.0,18.0]\n", "state": "COMPLETED"}}
    ```
* Remove the lingering workflow instance artifacts using `flowctl delete`.
    ```console
    % python -m flowctl delete flow-8188a784f37b11ea9ac2acde48001122
    2020-09-10 10:37:55,735|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"flow-8188a784f37b11ea9ac2acde48001122": {"result": 0, "message": "Successfully deleted flow-8188a784f37b11ea9ac2acde48001122."}}
    ```
* Stop the workflow deployment using `flowctl stop`.
    ```console
    % python -m flowctl stop --kind DEPLOYMENT $WF_PROC
    2020-09-10 10:38:08,644|flowctl|INFO|stop_action.py:32|Got response: 0, "Ok", {"CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122": {"status": 0, "message": "Stopped."}}
    ```
* Verify the workflow deployment has verifiably stopped using `flowctl ps`, again,
  paying attention to the reported state, waiting for the `STOPPED` state.
    ```console
    % watch python -m flowctl ps --kind DEPLOYMENT
    ```
* Remove the workflow deployment from the system using `flowctl delete`.
    ```console
    % python -m flowctl delete --kind DEPLOYMENT $WF_PROC
    2020-09-10 10:38:28,293|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122": {"result": 0, "message": "Successfully deleted CalcProcess-5dc0f6bcf37b11ea9ac2acde48001122."}}
    ```

Summary/TL;DR
=============

The following presents a summary of command line inputs to run the demonstration.
```console
% python -m flowctl apply calcprocess.bpmn
% watch python -m flowctl ps --kind DEPLOYMENT
% python -m flowctl ps --kind DEPLOYMENT
% WF_PROC=CalcProcess-...
% python -m flowctl run $WF_PROC 1 2 3
% python -m flowctl ps
% python -m flowctl delete flow-...
% python -m flowctl stop --kind DEPLOYMENT $WF_PROC
% watch python -m flowctl ps --kind DEPLOYMENT
% python -m flowctl delete --kind DEPLOYMENT $WF_PROC
```

References
==========

* Flask microservice inspired by https://www.docker.com/blog/containerized-python-development-part-1/.
