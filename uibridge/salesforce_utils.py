"""
Generate a Salesforce Schema from Workflow Task form 
"""
import json
import logging
import os

from io import BytesIO
from simple_salesforce import Salesforce
from uibridge.flowd_api import Workflow, WorkflowTask
from zipfile import ZipFile, ZipInfo

from flowlib.etcd_utils import locked_call
from flowlib.constants import (
    WorkflowKeys,
    WorkflowInstanceKeys,
)

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
                'field_map' : field_map
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

def put_salesforce_info(did:str, tid:str, data:str):
    # make sure data is encoded
    if isinstance(data, dict):
        data = json.dumps(data).encode()
    elif isinstance(data, str):
        data = data.encode()

    assert isinstance(data,bytes), 'Data must be bytes'

    key = WorkflowKeys.salesforce_info(did, tid)
    def __logic(etcd):
        logging.info(f'salesforce writing {data}')
        etcd.put(key, data)
        return True
    return locked_call(key, __logic)

def get_salesforce_info(did:str, tid:str) -> dict:
    key = WorkflowKeys.salesforce_info(did, tid)
    def __logic(etcd):
        data, _ = etcd.get(key)
        if data is not None:
            return json.loads(data.decode())
        return None
    return locked_call(key, __logic)

def get_salesforce_client() -> Salesforce:
    server_key_path=os.path.join(os.path.dirname(__file__), 'resources/server.key')
    return Salesforce(
        username='ghester@rexhomes.com.qa1',
        consumer_key='3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk',
        privatekey_file=server_key_path, #'/root/JWT/server.key',
        domain='test',
    )

def create_salesforce_assets(wf:Workflow):
    # TODO: have to derive path to server key
    # TODO: Move all these constants to either etcd
    sf = get_salesforce_client()

    obj_exists = 0
    objects = []
    pr = Profile('System Administrator (MFA)')
    did_pref = wf.did
    #
    # we are constrained in Salesforce Profile's to 40-chars, and since we waste
    # six with the __c for the CustomObject name AND the CustomField name AND
    # one more for the dot separator, then we're down six leaving 33 total. Hence
    # we restrict the did and tid names to six chars each. If the name is already
    # six or less then use verbatim, otherwise condense by taking the first and
    # last three chars of the name. Subtract these 12 chars and that means the
    # maximum length of a field name to 21 chars, which should suffice.
    if len(did_pref) > 6:
        did_pref = wf.did[0:3] + wf.did[-3:]

    # create a file heir as follows:
    # ./package.xml
    # ./objects
    # ./objects/name_of_first_object__c.object
    # ./objects/name_of_second_object__c.object
    # ...
    archive = BytesIO()
    with ZipFile(archive, 'w') as zip_archive:
        filex = ZipInfo('package.xml')
        zip_archive.writestr(filex, package_xml)

        task:WorkflowTask
        for task in wf.tasks.values():
            # did/tid combo can't exceed 12 chars
            tid_pref = task.tid
            if len(tid_pref) > 6:
                tid_pref = task.tid[0:3] + task.tid[-3:]
            obj = CustomObject(f'rf{did_pref}_{tid_pref}', wf.did)
            objects.append(obj)
            pr.add_obj(obj)
            form = task.get_form(None,False)

            for field in form:
                cf = CustomField(field['dataId'], field['label'], 'Text', 180)
                obj.add_field(cf)

            # save the salesinfo json
            j = obj.form_json()
            logging.info(j)
            put_salesforce_info(wf.did, task.tid, j)

            if obj.exists(sf):
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
    result = sf.deploy('/opt/rexflow/bogus.zip', True, allowMissingFiles=True, testLevel='NoTestRun')
    async_id = result['asyncId']
    deployment_finished = False
    successful          = False
    while not deployment_finished:
        result = sf.checkDeployStatus(async_id, True)
        logging.info(result)
        deployment_finished = result.get('state') in ["Succeeded", "Completed", "Error", "Failed", "SucceededPartial", None]
        successful          = result.get('state') in ["Succeeded", "Completed"]

    return successful, len(objects)

def post_salesforce_data(did:str, iid:str, task:WorkflowTask, data:dict):
    """
    """
    sf_id = None
    sf_info = get_salesforce_info(task.wf.did, task.tid)
    assert sf_info is not None, f'{task.wf.did} {task.tid} does not have salesforce support'
    sf = get_salesforce_client()
    data_dict = {}
    data_dict['did__c'] = did
    data_dict['iid__c'] = iid
    data_dict['tid__c'] = task.tid
    data_dict['xid__c'] = 'n/a'
    logging.info(f'form data {data}\n sf_info {sf_info}')
    for rf_key, sf_key in sf_info['salesforce']['field_map'].items():
        if rf_key in data.keys():
            data_dict[sf_key] = data[rf_key]['data']

    logging.info(f'salesforce posting {data_dict}')
    sf_obj = getattr(sf, sf_info['salesforce']['table'])
    if sf_id is not None:
        response = sf_obj.upsert(sf_id, data_dict)
    else:
        response = sf_obj.create(data_dict)

    # [('id', 'a1S02000000WGUaEAO'), ('success', True), ('errors', [])]
    logging.info(f'salesforce response {response}')
    if 'id' in response.keys():
        # the response has a record id, which we will need in case we need to update this record.
        # sf_id = response['id']
        pass



    # result = sf.Rexflow_amorttable_7e262634_show_table__c.create({'interest__c':'0.030', 'principal__c':'123456.00', 'seller__c':'REX Homes', 'term__c': '30'})
