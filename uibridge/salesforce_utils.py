"""
Generate a Salesforce Schema from Workflow Task form
"""
import json
import logging
import os
import queue

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from simple_salesforce import Salesforce
from typing import Any
from uibridge.flowd_api import Workflow, WorkflowTask
from zipfile import ZipFile, ZipInfo

from flowlib.constants import (
    WorkflowKeys,
    WorkflowInstanceKeys,
)
from flowlib.etcd_utils import locked_call
from flowlib.executor import get_executor


private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA/USE/o9vB/k6CEPm6sIjcPUiY0rw+jAhRiLJR1wUX9CuJ1+f
x/buK0Vqq59cm2bf1eWYIp0J6uqHG8A44xp89oXR6/DmJnJWBi8CRmyjRDNMpnIq
VgmjDuFXndKWkyHpyhgVtPIA3Bi+3UHQXbGX8E/rYXea28XQ7/HxybG9YHvJXZhn
Bwqo8CmUFk+b7mjpwYd4i9cRsVtPDe9Mvf+1VWcGj+bWTAVFTGSjBknzCzJI3Yvh
AzhPYK3Zhxi7m/eWEYOPCYPRFxq7gijkaQq2szPYEq20N8r1pWgjXZPmCd/UQ0Ek
WHwGYrcmBPirO2/wpJJgQrhbTpMcsZTmw5v5dQIDAQABAoIBAE8TS6rnQbVtnS7j
dH+rqcEk6F20ElUrHdh2F/4Nw9a+owFsG8klUet0uv9mvFVQ42Y3Ty7PdT9Bhnml
pJ1TsdyOn6JZDqLGZBF+L+mpFbi/g5kcYBeI3r5QoTiHfbfmiMYuiuh5/sa5ey49
1D7MqjG/4jAGVfV0Z+3izqk4s3Yh0RXU3KbYKVvJlPSAfiRsH8f/IvgIsux8bsCD
4+tEg2hBvLLlml9AIHC06S82w/xYBggXje550eMKtERl5bFlk+AIVYTo2bUzpFCX
WViv3JC7/6P6E/y6W4xSnaXLlvY+yeKotXkW0XReph/Q1TopI4rzF6VojlmSG3KB
CYo+EgECgYEA/8s+j9v54XqBYgozMVq17KcK8NGZFXWJDEeAHNN/DwblSRKTIDRb
LQp+H6OP6Rq/jWcQUDp35XwThSw5r6Lsv6Xa0yo2/05c58yCJxNvwIfduIs0emxQ
Wc4JjP2o/2PbqLVLcFNIjw8jAg7+KGapRs1tC63MXsRQJArMPjsXZsECgYEA/XjB
DNgVGvvQK92m7hTCX+nuqx51mOGs1mSdhcCCnjCdwLwHQNQmG4zGPHjFjxeoUx6i
uYUFK2b8LJTLjbIWzqTBtiBtfY85XdpjR/SuFncYkHqQ0ms9c5jwA/2qb1IYfIHx
GPYov/m5MR3aBPuuPuUzQpwTWV6+HebPHQtwE7UCgYEAgoSSR5VWy1ZW7k+GD4jZ
iwcw7fAEzI5Mf5d8JzlDe8do9wAjUitk2nagJESxCaA8XUpZaJZs1wuYajtGs/fO
FXvrTBQeO+cgQKZ5QrcILpUk7SUagd0CotAez3Ie6TFqw4q+E3Jrc5OlqUc9KCA5
/4aSPYNQ5IoG2l0oGhjMuAECgYEAzBgJSfBLvjh4vHlzSk0I3fYdKUgTZJCCfPbz
J5mFEx8ORvyf0oGAVbqafGK6oKdp79PBLyR+rx3ze2osJOH7H1TmbWHbB7jldj68
plnMO2aWLu+h4OxcxNGmoXAFZjFyaf6vRWwgD8Ria7wfqteEzDv9dGr74YA6ERWi
Oz7UdekCgYBslAlmMi8kmtx34GS+STe03xbiO9YtIs2/1qiYF1DQhlpJcDEC/Xtr
1UkbKUxLxAL8kL+9onIrUKM8Re3kdA/qFfiLCHpMBhmtUMA0unQQcY2QhXddyzFz
7Ts84zwHLQ0QpzTxiWO1j3TBJl59j1arhoB2ecnyT/tsULkR+h9YNQ==
-----END RSA PRIVATE KEY-----"""

class CustomField:
    def __init__(self, name:str, label:str, type:str, length:int):
        # remove all '-' and '_' and convert to lower case
        self._name = f'{name.replace("-","").replace("_","")}__c'.lower()
        self._form_name = name
        self._label = label
        self._type = type
        self._length = length

    def __str__(self):
        return f"""
<fields>
    <fullName>{self._name}</fullName>
    <externalId>false</externalId>
    <label>{self._label}</label>
    <length>{self._length}</length>
    <required>false</required>
    <trackHistory>false</trackHistory>
    <trackTrending>false</trackTrending>
    <type>{self._type}</type>
</fields>
"""

class CustomObject:
    def __init__(self, name:str, label:str):
        # remove all '-' and '_' and convert to lower case
        self._name = f'{name.replace("-","").replace("_","")}__c'.lower()
        self._label = label
        self._fields:list[CustomField] = []
        # insert here any common fields
        self.add_field(CustomField('did', 'Workflow Id', 'Text', 180))
        self.add_field(CustomField('iid', 'Workflow Instance Id', 'Text', 180))
        self.add_field(CustomField('tid', 'Workflow Task Id', 'Text', 180))
        self.add_field(CustomField('xid', 'Workflow Task Exchange Id', 'Text', 180))

    def exists(self, sf:Salesforce):
        """Determine if this custom object already exists"""
        try:
            getattr(sf,self._name).metadata()
            sf.query_all('SELECT Id FROM {}'.format(self._name))['records']
            return True
        except:
            pass
        return False

    def add_field(self, fld:CustomField):
        self._fields.append(fld)

    def __str__(self):
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <allowInChatterGroups>false</allowInChatterGroups>
    <compactLayoutAssignment>SYSTEM</compactLayoutAssignment>
    <deploymentStatus>Deployed</deploymentStatus>
    <enableActivities>false</enableActivities>
    <enableBulkApi>true</enableBulkApi>
    <enableFeeds>false</enableFeeds>
    <enableHistory>true</enableHistory>
    <enableLicensing>false</enableLicensing>
    <enableReports>true</enableReports>
    <enableSearch>true</enableSearch>
    <enableSharing>true</enableSharing>
    <enableStreamingApi>true</enableStreamingApi>
    <externalSharingModel>Private</externalSharingModel>
    <label>Rexflow {self._name}</label>
    <nameField>
        <label>Rexflow_{self._name}</label>
        <trackHistory>false</trackHistory>
        <type>Text</type>
    </nameField>
    <pluralLabel>Rexflow {self._label}s</pluralLabel>
    <searchLayouts/>
    <sharingModel>ReadWrite</sharingModel>
    <visibility>Public</visibility>
"""

        field:CustomField
        for field in self._fields:
            xml += str(field)
        xml += '</CustomObject>'
        return xml

    def form_json(self) -> str:
        field_map = {}
        for field in self._fields:
            field_map[field._form_name] = field._name

        d = {'salesforce': {
                'table' : self._name,
                'field_map' : field_map,
                'records' : {},
            }
        }
        return json.dumps(d)

class Profile:
    def __init__(self, name:str):
        self._name = name
        self._objs = []

    def add_obj(self, obj:CustomObject):
        self._objs.append(obj)

    def __str__(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Profile xmlns="http://soap.sforce.com/2006/04/metadata">
        <userPermissions>
            <enabled>true</enabled>
            <name>ApiEnabled</name>
        </userPermissions>
"""
        for obj in self._objs:
            for field in obj._fields:
                label = f'{obj._name}.{field._name}'
                assert len(label) < 41, f'boom! {label} exceeds max length'
                xml += f"""<fieldPermissions>
            <field>{label}</field>
            <editable>true</editable>
            <hidden>false</hidden>
            <readable>true</readable>
        </fieldPermissions>
"""

        xml += '</Profile>'
        return xml

package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <name>CustomObject</name>
        <members>*</members>
    </types>
    <types>
        <name>CustomField</name>
        <members>*</members>
    </types>
    <types>
        <name>Profile</name>
        <members>*</members>
    </types>
    <version>52.0</version>
    <fullName>rexflow_model</fullName>
</Package>
"""

class SalesforceManager:
    def __init__(self, wf:Workflow, profile:dict):
        self._wf = wf
        self._queue = queue.Queue()
        self._executor:ThreadPoolExecutor = get_executor()
        self._future = None
        self._profile = profile
        self._sf = self.get_client()

    def start(self):
        assert self._future is None
        self._running = True
        self._future = self._executor.submit(self)

    def stop(self):
        assert self._future is not None
        # exhaust the queue
        self._queue.join()
        self._running = False

    def put_salesforce_info(self, tid:str, data:Any):
        # make sure data is encoded
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        elif isinstance(data, str):
            data = data.encode()

        assert isinstance(data,bytes), 'Data must be bytes'

        key = WorkflowKeys.salesforce_info(self._wf.did, tid)
        def __logic(etcd):
            logging.info(f'salesforce writing {data}')
            etcd.put(key, data)
            return True
        return locked_call(key, __logic)

    def __call__(self):
        while self._running:
            iid, task, data = self._queue.get()
            if iid is not None:
                self.post_salesforce_data(iid, task, data)
                logging.info("processed event successfully.")
            self._queue.task_done()

    def post(self, iid:str, task:WorkflowTask, data:dict):
        self._queue.put([iid, task, data])

    def get_salesforce_info(self, tid:str) -> dict:
        key = WorkflowKeys.salesforce_info(self._wf.did, tid)
        def __logic(etcd):
            data, _ = etcd.get(key)
            if data is not None:
                return json.loads(data.decode())
            return None
        return locked_call(key, __logic)

    def get_client(self) -> Salesforce:
        return Salesforce(
            username=self._profile['username'], #'ghester@rexhomes.com.qa1',
            consumer_key=self._profile['consumer_key'], #'3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk',
            privatekey=self._profile['private_key'],
            domain=self._profile['domain']
        )

    def get_salesforce_object_name(self, name:str):
        # If the name is already six or less then use verbatim, otherwise
        # condense by taking the first and last three chars of the name.
        if len(name) > 6:
            name = name[0:3] + name[-3:]
        return name

    def get_salesforce_table_name(self, task:WorkflowTask):
        # we are constrained in Salesforce Profile(s) to 40-chars, and since we waste
        # six with the __c for the CustomObject name AND the CustomField name AND
        # one more for the dot separator, then we're down six leaving 33 total. Hence
        # we restrict the did and tid names to six chars each. Subtract these 12 chars
        # and that means the maximum length of a field name to 22 chars, which should
        # suffice.
        #
        # So a salesforce CustomObject name will be rfwwwwww_tttttt__c (18 chars)
        did_pref = self.get_salesforce_object_name(task.wf.did)
        tid_pref = self.get_salesforce_object_name(task.tid)
        return f'rf{did_pref}{tid_pref}'

    def create_salesforce_assets(self):
        # TODO: have to derive path to server key
        # TODO: Move all these constants to either etcd
        obj_exists = 0
        objects = []
        pr = Profile('System Administrator (MFA)')

        # create a file heir as follows:
        # ./package.xml
        # ./objects
        # ./objects/name_of_first_object__c.object
        # ./objects/name_of_second_object__c.object
        # ./objects/...
        # ./profiles/name_of_account.profile
        # ...
        archive = BytesIO()
        with ZipFile(archive, 'w') as zip_archive:
            filex = ZipInfo('package.xml')
            zip_archive.writestr(filex, package_xml)

            task:WorkflowTask
            for task in self._wf.tasks.values():
                obj = CustomObject(self.get_salesforce_table_name(task), self._wf.did)
                objects.append(obj)
                pr.add_obj(obj)
                form = task.get_form(None,False)

                for field in form:
                    cf = CustomField(field['dataId'], field['label'], 'Text', 180)
                    obj.add_field(cf)

                # save the salesinfo json
                j = obj.form_json()
                logging.info(j)
                self.put_salesforce_info(task.tid, j)

                if obj.exists(self._sf):
                    # validate the the object does now already exist
                    logging.info(f'{obj._name} already exists - skipping')
                    obj_exists += 1
                    continue

                filex = ZipInfo(f'objects/{obj._name}.object')
                obj_xml = str(obj)
                zip_archive.writestr(filex, obj_xml)
                logging.info(obj_xml)

            # now write the Admin profile (updates)
            filex = ZipInfo(f'profiles/{pr._name}.profile')
            pro_xml = str(pr)
            zip_archive.writestr(filex, pro_xml)
            logging.info(pro_xml)

        if len(objects) == 0:
            logging.info("No objects to create - leaving")
            return True, obj_exists

        with open('bogus.zip', 'wb') as f:
            f.write(archive.getbuffer())

        archive.close()

        # now deploy the schema to salesforce
        result = self._sf.deploy('/opt/rexflow/bogus.zip', True, allowMissingFiles=True, testLevel='NoTestRun')
        async_id = result['asyncId']
        deployment_finished = False
        successful          = False
        while not deployment_finished:
            result = self._sf.checkDeployStatus(async_id, True)
            logging.info(result)
            deployment_finished = result.get('state') in ["Succeeded", "Completed", "Error", "Failed", "SucceededPartial", None]
            successful          = result.get('state') in ["Succeeded", "Completed"]

        return successful, len(objects)

    def post_salesforce_data(self, iid:str, task:WorkflowTask, data:dict):
        """
        """
        sf_info = self.get_salesforce_info(task.tid)
        assert sf_info is not None, f'{self._wf.did} {task.tid} does not have salesforce support'
        if 'records' not in sf_info:
            sf_info['records'] = {}
        sf_recid = sf_info['records'].get(iid, None)
        data_dict = {}
        data_dict['did__c'] = self._wf.did
        data_dict['iid__c'] = iid
        data_dict['tid__c'] = task.tid
        data_dict['xid__c'] = 'n/a'
        logging.info(f'form data {data}\n sf_info {sf_info}')
        for rf_key, sf_key in sf_info['salesforce']['field_map'].items():
            if rf_key in data.keys():
                data_dict[sf_key] = data[rf_key]['data']

        logging.info(f'salesforce posting {data_dict}')
        sf_obj = getattr(self._sf, sf_info['salesforce']['table'])
        if sf_recid is not None:
            response = sf_obj.upsert(sf_recid, data_dict)
        else:
            response = sf_obj.create(data_dict)
            if 'id' in response.keys():
                # the response has a record id, which we will need in case we need to update this record.
                sf_info['records'][iid] = response['id']
                self.put_salesforce_info(task.tid, sf_info)

        # [('id', 'a1S02000000WGUaEAO'), ('success', True), ('errors', [])]
        logging.info(f'salesforce response {response}')



    # result = sf.Rexflow_amorttable_7e262634_show_table__c.create({'interest__c':'0.030', 'principal__c':'123456.00', 'seller__c':'REX Homes', 'term__c': '30'})
