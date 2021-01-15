
coverage.py can be used to measure coverage and set the errorlevel ($? in bash) to 2 if a minimum coverage is not acheived.

We run coverage limiting the analysis to the flowlib itself, else all imports are included.

$ coverage run --source=flowlib -m unit
 TestBPMNComponent
==============================
....
 TestBpmnCatchEvent
==============================
..
 TestBpmnProcess
==============================
.......
 TestBpmnUtil
==============================
.........
 TestCallProperties
==============================
.....
 TestConstants
==============================
......
 TestEtcdDict
==============================
{'/a/b/c/d': {'e': {'a': 'hello', 'b': 'world'}}}
F.
 TestEtcdUtils
==============================
.......
 TestHealthProperties
==============================
......
 TestServiceProperties
==============================
.....
 TestTransitionState
==============================
ERROR:root:State transition failed! statekey : those -> them
.ERROR:root:State transition failed! statekey : this -> them
..
 TestWorkflowProperties
==============================
........
======================================================================
FAIL: test_from_dict_complex (tests.unit.test_etcd_utils.TestEtcdDict)
EtcdDict with complex dict returns something weird
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/ghester/work/rexflow/tests/unit/test_etcd_utils.py", line 128, in test_from_dict_complex
    self.assertEqual(res,otDict)
AssertionError: {'/a/b/c/d': {'e': {'a': 'hello', 'b': 'world'}}} != {}

----------------------------------------------------------------------
Ran 64 tests in 0.033s

FAILED (failures=1)

$ coverage report --fail-under=90 
Name                                                      Stmts   Miss  Cover
-----------------------------------------------------------------------------
/home/ghester/work/rexflow/flowlib/__init__.py                0      0   100%
/home/ghester/work/rexflow/flowlib/bpmn.py                  116     47    59%
/home/ghester/work/rexflow/flowlib/bpmn_util.py             277     10    96%
/home/ghester/work/rexflow/flowlib/catch_event.py            31     12    61%
/home/ghester/work/rexflow/flowlib/constants.py              87      1    99%
/home/ghester/work/rexflow/flowlib/end_event.py              37     16    57%
/home/ghester/work/rexflow/flowlib/envoy_config.py           25     25     0%
/home/ghester/work/rexflow/flowlib/etcd_utils.py            107     43    60%
/home/ghester/work/rexflow/flowlib/exclusive_gateway.py      56     46    18%
/home/ghester/work/rexflow/flowlib/executor.py               10     10     0%
/home/ghester/work/rexflow/flowlib/flow_pb2.py               50     50     0%
/home/ghester/work/rexflow/flowlib/flow_pb2_grpc.py          59     59     0%
/home/ghester/work/rexflow/flowlib/flowd_utils.py            15     15     0%
/home/ghester/work/rexflow/flowlib/k8s_utils.py              14     10    29%
/home/ghester/work/rexflow/flowlib/quart_app.py              29     29     0%
/home/ghester/work/rexflow/flowlib/start_event.py            35     17    51%
/home/ghester/work/rexflow/flowlib/task.py                   54     39    28%
/home/ghester/work/rexflow/flowlib/throw_event.py            32     20    38%
/home/ghester/work/rexflow/flowlib/workflow.py              175    175     0%
-----------------------------------------------------------------------------
TOTAL                                                      1209    624    48%
Coverage failure: total of 48 is less than fail-under=90

$ echo $?
2
