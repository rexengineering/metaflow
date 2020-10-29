#!/usr/bin/env bash

flowctl () {
    python -m flowctl $@
}

wait_for_state () {
    KIND=$1
    STATE_QUERY=$2
    DESIRED_STATE=$3
    CRNT_STATE=$(flowctl ps -o -k ${KIND} | jq -r ${STATE_QUERY})
    [ "$CRNT_STATE" != "" ] || return 1
    while [ "$CRNT_STATE" != "$DESIRED_STATE" ]; do
        sleep 5
        CRNT_STATE=$(flowctl ps -o -k ${KIND} | jq -r ${STATE_QUERY})
        [ "$CRNT_STATE" != "" ] || return 1
    done
    return 0
}

clean_up () {
    (
        flowctl delete $1 &&
        flowctl stop -k DEPLOYMENT $2 &&
        wait_for_state DEPLOYMENT ".[\"$2\"].state" STOPPED &&
        flowctl delete -k DEPLOYMENT $2
    ) || return 1
    return 0
}

main() {
    echo "Step 1: (Re)build the Docker images..."
    python -m build --clean || return 1

    echo
    echo "Step 2: Submit workflow for deployment..."
    WF_DEPLOYMENT=$(flowctl apply -o underpants.bpmn | jq -r .Underpants)
    echo "WF_DEPLOYMENT=$WF_DEPLOYMENT"
    [ "$WF_DEPLOYMENT" != "" ] || return 2

    echo
    echo "Step 3: Wait for the deployment to be available..."
    wait_for_state  DEPLOYMENT ".[\"$WF_DEPLOYMENT\"].state" RUNNING || return 3

    echo
    echo "Step 4: Run a workflow instance..."
    WF_INSTANCE=$(flowctl run -o $WF_DEPLOYMENT | jq -r ".[\"$WF_DEPLOYMENT\"]")
    echo "WF_INSTANCE=$WF_INSTANCE"
    [ "$WF_INSTANCE" != "" ] || return 4

    echo
    echo "Step 5: Wait for the instance to complete..."
    wait_for_state INSTANCE ".[\"$WF_INSTANCE\"].state" COMPLETED || return 5

    echo
    echo "Step 6: Check the result..."
    RESULT=$(flowctl ps -o 2> /dev/null | jq -r .\[\"$WF_INSTANCE\"\].result)
    [ "$RESULT" != "" ] || return 6
    (echo "$RESULT" | jq .) || return 6

    echo
    echo "Step 7: Clean up..."
    clean_up $WF_INSTANCE $WF_DEPLOYMENT || return 7

    return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main $@
    exit $?
fi
