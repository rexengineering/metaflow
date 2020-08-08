Running the Example
===================

* Setup operating environment per the [top-level REAMDME](../../README.md).
* Build a Docker image for the test server.
    ```zsh
    % docker build -t calc_2_x_to_2 .
    ```
* Deploy a workflow using `flowctl`, passing the example's BPMN file as an argument to the `apply` subcommand.
    ```zsh
    % python -m flowctl apply calcprocess.bpmn
    2020-08-07 18:31:03,753|flowctl|INFO|apply_action.py:59|Got response: 0, "Ok", {"CalcProcess": "CalcProcess-0ec1a398d90611ea9ec3acde48001122"}
    ```
* Verify the workflow has deployed using `flowctl ps`, paying particular attention
  to the state of the deployment, waiting for the `RUNNING` state.
    ```zsh
    % python -m flowctl ps --kind DEPLOYMENT
    2020-08-07 18:33:04,913|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {"CalcProcess-0ec1a398d90611ea9ec3acde48001122": {"state": "RUNNING"}}
    ```
* Run a worflow instance using `flowctl run`.
    ```
    TBD...
    ```
* Wait for results from the workflow instance using `flowctl ps`.
    ```
    TBD...
    ```
* Remove the lingering workflow instance artifacts using `flowctl delete`.
    ```
    TBD...
    ```
* Stop the workflow deployment using `flowctl stop`.
    ```zsh
    % python -m flowctl stop --kind DEPLOYMENT CalcProcess-0ec1a398d90611ea9ec3acde48001122
    2020-08-07 18:45:43,894|flowctl|INFO|stop_action.py:32|Got response: 0, "Ok", {"CalcProcess-0ec1a398d90611ea9ec3acde48001122": {"status": 0, "message": "Stopped."}}
    ```
* Verify the workflow deployment has verifiably stopped using `flowctl ps`, again,
  paying attention to the reported state, waiting for the `STOPPED` state.
    ```zsh
    % python -m flowctl ps --kind DEPLOYMENT
    2020-08-07 18:50:08,170|flowctl|INFO|ps_action.py:35|Got response: 0, "Ok", {"CalcProcess-0ec1a398d90611ea9ec3acde48001122": {"state": "STOPPED"}}
    ```
* Remove the workflow deployment from the system using `flowctl delete`.
    ```zsh
    % python -m flowctl delete --kind DEPLOYMENT CalcProcess-0ec1a398d90611ea9ec3acde48001122
    2020-08-07 18:52:40,306|flowctl|INFO|delete_action.py:33|Got response: 0, "Ok", {"CalcProcess-0ec1a398d90611ea9ec3acde48001122": {"result": 0, "message": "Successfully deleted CalcProcess-0ec1a398d90611ea9ec3acde48001122."}}
    ```

References
==========

* Flask microservice inspired by https://www.docker.com/blog/containerized-python-development-part-1/.
