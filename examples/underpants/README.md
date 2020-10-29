Running the Example
===================

* Setup operating environment per the [top-level REAMDME](../../README.md).
* Build the server containers using the `build.py` module.
    ```console
    % python -m build --clean
    ```
* Deploy the workflow using the `apply` sub-command to `flowctl`.
    ```console
    % python -m flowctl apply underpants.bpmn
    2020-09-11 10:45:50,014|flowctl|INFO|apply_action.py:59|Got response: 0, "Ok", {"Underpants": "Underpants-daf84dc2f44511ea930aacde48001122"}
    % WF_PROC=Underpants-daf84dc2f44511ea930aacde48001122
   ```
* Wait for the deployment to enter the `RUNNING` state.
    ```console
    % watch python -m flowctl ps --kind DEPLOYMENT
    ```
* Create and run a workflow instance using the `run` sub-command.
    ```console
    % python -m flowctl run $WF_PROC
    2020-09-11 10:46:39,279|flowctl|INFO|run_action.py:35|Got response: 0, "Ok", {"Underpants-daf84dc2f44511ea930aacde48001122": "flow-fb364c74f44511ea930aacde48001122"}
    ```
* Wait for the instance to enter the `COMPLETED` state, and observe the results.
    ```console
    % watch python -m flowctl ps
    % python -m flowctl ps
    2020-09-11 10:47:33,317|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {"flow-fb364c74f44511ea930aacde48001122": {"result": "{\"cashflow\":\"Positive!\",\"sauce\":\"Applied.\",\"underpants\":\"Collected.\"}\n", "state": "COMPLETED"}}
    ```
* Clean up the instance data using the `delete` sub-command.
    ```console
    % python -m flowctl delete flow-fb364c74f44511ea930aacde48001122
    2020-09-11 10:47:52,051|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"flow-fb364c74f44511ea930aacde48001122": {"result": 0, "message": "Successfully deleted flow-fb364c74f44511ea930aacde48001122."}}
    ```
* Stop the deployment using the `stop` sub-command, and wait for the deployment
    to enter the `STOPPED` state.
    ```console
    % python -m flowctl stop --kind DEPLOYMENT $WF_PROC
    2020-09-11 10:48:20,466|flowctl|INFO|stop_action.py:32|Got response: 0, "Ok", {"Underpants-daf84dc2f44511ea930aacde48001122": {"status": 0, "message": "Stopped."}}
    % watch python -m flowctl ps --kind DEPLOYMENT
   ```
* Remove any deployment data using the `delete` sub-command.
    ```console
    % python -m flowctl delete --kind DEPLOYMENT $WF_PROC
    2020-09-11 10:49:05,143|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"Underpants-daf84dc2f44511ea930aacde48001122": {"result": 0, "message": "Successfully deleted Underpants-daf84dc2f44511ea930aacde48001122."}}
    ```

Summary/TL;DR
=============

```console
% python -m build --clean
% python -m flowctl apply underpants.bpmn
% watch python -m flowctl ps --kind DEPLOYMENT
% WF_PROC=Underpants-...
% python -m flowctl run $WF_PROC
% watch python -m flowctl ps
% python -m flowctl ps
% python -m flowctl delete flow-...
% python -m flowctl stop --kind DEPLOYMENT $WF_PROC
% watch python -m flowctl ps --kind DEPLOYMENT
% python -m flowctl delete --kind DEPLOYMENT $WF_PROC
```
