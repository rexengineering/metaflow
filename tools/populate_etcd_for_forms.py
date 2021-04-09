hive = {
    'rexflow': {
        'instances': {
            'tde-15839350-35a7de06922d11eb909312e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["1bc8b9751f0b9053adf4d9ca0fe9f1c2"]'
            }, 
            'tde-15839350-3b6f4742922411ebb236020fd53bd6fc': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'ERROR', 
                'traceid': b'["de2a23123b4bc11f2fbcae86bf956096"]'
            }, 
            'tde-15839350-86c5393e922611eb9c0512e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'STARTING', 
                'traceid': b'["ead4def91dbf1557ca8435e4ee7292fc"]'
            }, 
            'tde-15839350-a9e1ccda922511eba57312e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'STOPPING', 
                'traceid': b'["447da28650dbbf27c7d3328440d436c1"]'
            }, 
            'tde-15839350-b1d2742a922611ebbd9012e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'RUNNING', 
                'traceid': b'["54a7594c0155a82ef89ea53289f2894e"]'
            }, 
            'tde-15839350-de48766c922611eba3e412e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839350', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["c9e8d6f845d20bde76e69b4f53007485"]'
            },
            'tde-15839351-35a7de06922d11eb909312e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839351', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["1bc8b9751f0b9053adf4d9ca0fe9f1c2"]'
            }, 
            'tde-15839351-3b6f4742922411ebb236020fd53bd6fc': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839351', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["de2a23123b4bc11f2fbcae86bf956096"]'
            }, 
            'tde-15839351-86c5393e922611eb9c0512e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839351', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["ead4def91dbf1557ca8435e4ee7292fc"]'
            }, 
            'tde-15839351-a9e1ccda922511eba57312e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839351', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["447da28650dbbf27c7d3328440d436c1"]'
            }, 
            'tde-15839351-b1d2742a922611ebbd9012e9eb4c0897': {
                'content_type': b'application/json', 
                'end_event': b'e1', 
                'parent': b'tde-15839351', 
                'result': b'[]', 
                'state': b'COMPLETED', 
                'traceid': b'["54a7594c0155a82ef89ea53289f2894e"]'
            }, 
        }, 
        'workflows': {
                'tde-15839350': {
                    'probes': {
                        'Event_0zti09t': b'UP', 
                        'TD1': b'UP'
                    }, 
                    'proc': b'<?xml version="1.0" encoding="utf-8"?>\n<bpmn:process id="TDE" isExecutable="true"><bpmn:startEvent id="TD1" name="TD1"><bpmn:outgoing>Flow_0wd3saa</bpmn:outgoing><bpmn:timerEventDefinition id="TimerEventDefinition_1wvovav"><bpmn:timeDate xsi:type="bpmn:tFormalExpression">2021-03-30T11:52:00Z</bpmn:timeDate></bpmn:timerEventDefinition></bpmn:startEvent><bpmn:sequenceFlow id="Flow_0wd3saa" sourceRef="TD1" targetRef="Event_0zti09t"></bpmn:sequenceFlow><bpmn:endEvent id="Event_0zti09t" name="E1"><bpmn:incoming>Flow_0wd3saa</bpmn:incoming></bpmn:endEvent><bpmn:textAnnotation id="TextAnnotation_0pi6u8h"><bpmn:text>rexflow_global_properties:\n\xc2\xa0 \xc2\xa0 recoverable: true\n\xc2\xa0 \xc2\xa0 id: tde\n\xc2\xa0 \xc2\xa0 xgw_expression_type: feel</bpmn:text></bpmn:textAnnotation></bpmn:process>', 
                    'state': b'RUNNING',
                    'fields': {
                        'Event_0zti09t': b'[{"id":"fname", "type":"TEXT", "order":1, "label":"First Name", "data":"", "encrypted":"True", "validators":[]},{"id":"lname", "type":"TEXT", "order":2, "label":"Last Name", "data":"", "encrypted":"True", "validators":[]},{"id":"addr1", "type":"TEXT", "order":3, "label":"Address 1", "data":"", "encrypted":"False", "validators":[]},{"id":"addr2", "type":"TEXT", "order":4, "label":"Address 2", "data":"", "encrypted":"False", "validators":[]},{"id":"city",  "type":"TEXT", "order":5, "label":"City", "data":"", "encrypted":"False", "validators":[]},{"id":"state", "type":"TEXT", "order":6, "label":"State", "data":"", "encrypted":"False", "validators":[]},{"id":"zip",   "type":"TEXT", "order":7, "label":"Zip Code", "data":"", "encrypted":"False", "validators":[]}]',
                        'TD1': b'[{"id":"fname", "type":"TEXT", "order":1, "label":"First Name", "data":"", "encrypted":"True", "validators":[]},{"id":"lname", "type":"TEXT", "order":2, "label":"Last Name", "data":"", "encrypted":"True", "validators":[]},{"id":"addr1", "type":"TEXT", "order":3, "label":"Address 1", "data":"", "encrypted":"False", "validators":[]},{"id":"addr2", "type":"TEXT", "order":4, "label":"Address 2", "data":"", "encrypted":"False", "validators":[]},{"id":"city",  "type":"TEXT", "order":5, "label":"City", "data":"", "encrypted":"False", "validators":[]},{"id":"state", "type":"TEXT", "order":6, "label":"State", "data":"", "encrypted":"False", "validators":[]},{"id":"zip",   "type":"TEXT", "order":7, "label":"Zip Code", "data":"", "encrypted":"False", "validators":[]}]'
                    }
                },
                'tde-15839351': {
                    'probes': {
                        'Event_0zti10t': b'UP', 
                        'TD2': b'UP'
                    }, 
                    'proc': b'<?xml version="1.0" encoding="utf-8"?>\n<bpmn:process id="TDE" isExecutable="true"><bpmn:startEvent id="TD1" name="TD1"><bpmn:outgoing>Flow_0wd3saa</bpmn:outgoing><bpmn:timerEventDefinition id="TimerEventDefinition_1wvovav"><bpmn:timeDate xsi:type="bpmn:tFormalExpression">2021-03-30T11:52:00Z</bpmn:timeDate></bpmn:timerEventDefinition></bpmn:startEvent><bpmn:sequenceFlow id="Flow_0wd3saa" sourceRef="TD1" targetRef="Event_0zti09t"></bpmn:sequenceFlow><bpmn:endEvent id="Event_0zti09t" name="E1"><bpmn:incoming>Flow_0wd3saa</bpmn:incoming></bpmn:endEvent><bpmn:textAnnotation id="TextAnnotation_0pi6u8h"><bpmn:text>rexflow_global_properties:\n\xc2\xa0 \xc2\xa0 recoverable: true\n\xc2\xa0 \xc2\xa0 id: tde\n\xc2\xa0 \xc2\xa0 xgw_expression_type: feel</bpmn:text></bpmn:textAnnotation></bpmn:process>', 
                    'state': b'RUNNING',
                    'fields': {
                        'Event_0zti10t': b'[{"id":"fname", "type":"TEXT", "order":1, "label":"First Name", "data":"", "encrypted":"True", "validators":[]},{"id":"lname", "type":"TEXT", "order":2, "label":"Last Name", "data":"", "encrypted":"True", "validators":[]},{"id":"addr1", "type":"TEXT", "order":3, "label":"Address 1", "data":"", "encrypted":"False", "validators":[]},{"id":"addr2", "type":"TEXT", "order":4, "label":"Address 2", "data":"", "encrypted":"False", "validators":[]},{"id":"city",  "type":"TEXT", "order":5, "label":"City", "data":"", "encrypted":"False", "validators":[]},{"id":"state", "type":"TEXT", "order":6, "label":"State", "data":"", "encrypted":"False", "validators":[]},{"id":"zip",   "type":"TEXT", "order":7, "label":"Zip Code", "data":"", "encrypted":"False", "validators":[]}]',
                        'TD2': b'[{"id":"fname", "type":"TEXT", "order":1, "label":"First Name", "data":"", "encrypted":"True", "validators":[]},{"id":"lname", "type":"TEXT", "order":2, "label":"Last Name", "data":"", "encrypted":"True", "validators":[]},{"id":"addr1", "type":"TEXT", "order":3, "label":"Address 1", "data":"", "encrypted":"False", "validators":[]},{"id":"addr2", "type":"TEXT", "order":4, "label":"Address 2", "data":"", "encrypted":"False", "validators":[]},{"id":"city",  "type":"TEXT", "order":5, "label":"City", "data":"", "encrypted":"False", "validators":[]},{"id":"state", "type":"TEXT", "order":6, "label":"State", "data":"", "encrypted":"False", "validators":[]},{"id":"zip",   "type":"TEXT", "order":7, "label":"Zip Code", "data":"", "encrypted":"False", "validators":[]}]'
                    }
                }
            }
        }
    }

from flowlib import etcd_utils as e

etcd = e.get_etcd()

def dumpkeys(p, h):
    global etcd
    if type(h) is dict:
        for k in h.keys():
            dumpkeys(f'{p}/{k}',h[k])
    else:
        # print(f'{p} {h}',flush=True)
        etcd.put(p,h)

if __name__ == '__main__':
    dumpkeys('',hive)
