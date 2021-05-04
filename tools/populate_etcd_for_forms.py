hive = {
    'rexflow': {
        'workflows': {
                'process-0p1yoqw-aa16211c': {
                    'fields': {
                        'Activity_144fvu9': b'[{"id":"fname", "type":"TEXT", "order":1, "label":"First Name", "data":"", "encrypted":"True", "validators":[]},{"id":"lname", "type":"TEXT", "order":2, "label":"Last Name", "data":"", "encrypted":"True", "validators":[]},{"id":"addr1", "type":"TEXT", "order":3, "label":"Address 1", "data":"", "encrypted":"False", "validators":[]},{"id":"addr2", "type":"TEXT", "order":4, "label":"Address 2", "data":"", "encrypted":"False", "validators":[]},{"id":"city",  "type":"TEXT", "order":5, "label":"City", "data":"", "encrypted":"False", "validators":[]},{"id":"state", "type":"TEXT", "order":6, "label":"State", "data":"", "encrypted":"False", "validators":[]},{"id":"zip",   "type":"TEXT", "order":7, "label":"Zip Code", "data":"", "encrypted":"False", "validators":[]}]',
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
