"""
Generate a Salesforce Schema from Workflow Task form 



<?xml version="1.0" encoding="UTF-8"?>
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
    <label>Bogus Code</label>
    <nameField>
        <label>Bogus Code Name</label>
        <trackHistory>false</trackHistory>
        <type>Text</type>
    </nameField>
    <pluralLabel>Bogus Codes</pluralLabel>
    <searchLayouts/>
    <sharingModel>ReadWrite</sharingModel>
    <visibility>Public</visibility>
    <fields>
        <fullName>BogusCity__c</fullName>
        <externalId>false</externalId>
        <label>City</label>
        <length>180</length>
        <required>false</required>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Text</type>
        <unique>false</unique>
    </fields>
    <fields>
        <fullName>BogusState__c</fullName>
        <externalId>false</externalId>
        <label>State</label>
        <required>false</required>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Picklist</type>
        <valueSet>
            <restricted>true</restricted>
            <valueSetName>US_States_USPS</valueSetName>
        </valueSet>
    </fields>
</CustomObject>
"""
import json

from io import BytesIO
from simple_salesforce import Salesforce
from uibridge.flowd_api import Workflow, WorkflowTask
from zipfile import ZipFile, ZipInfo

import flowlib.etcd_utils
from flowlib.constants import (
    WorkflowKeys,
    WorkflowInstanceKeys,
)
class CustomField:
    def __init__(self, name:str, label:str, type:str):
        # remove all '-' and '_' and convert to lower case
        self._name = f'{name.replace("-","").replace("_","")}__c'.lower()
        self._form_name = name
        self._label = label
        self._type = type

    def __str__(self):
        return '<fields>\n' \
            f'<fullName>{self._name}</fullName>\n' \
            '<externalId>false</externalId>\n' \
            f'<label>{self._label}</label>\n' \
            '<length>180</length>\n' \
            '<required>false</required>\n' \
            '<trackHistory>false</trackHistory>\n' \
            '<trackTrending>false</trackTrending>\n' \
            f'<type>{self._type}</type>\n' \
            '</fields>\n'

class CustomObject:
    def __init__(self, name:str, label:str):
        # remove all '-' and '_' and convert to lower case
        self._name = f'{name.replace("-","").replace("_","")}__c'.lower()
        self._label = label
        self._fields = []

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
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            '<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">\n' \
            '<allowInChatterGroups>false</allowInChatterGroups>\n' \
            '<compactLayoutAssignment>SYSTEM</compactLayoutAssignment>\n' \
            '<deploymentStatus>Deployed</deploymentStatus>\n' \
            '<enableActivities>false</enableActivities>\n' \
            '<enableBulkApi>true</enableBulkApi>\n' \
            '<enableFeeds>false</enableFeeds>\n' \
            '<enableHistory>true</enableHistory>\n' \
            '<enableLicensing>false</enableLicensing>\n' \
            '<enableReports>true</enableReports>\n' \
            '<enableSearch>true</enableSearch>\n' \
            '<enableSharing>true</enableSharing>\n' \
            '<enableStreamingApi>true</enableStreamingApi>\n' \
            '<externalSharingModel>Private</externalSharingModel>\n' \
            f'<label>Rexflow {self._name}</label>\n' \
            '<nameField>\n' \
                f'<label>Rexflow_{self._name}</label>\n' \
                '<trackHistory>false</trackHistory>\n' \
                '<type>Text</type>\n' \
            '</nameField>\n' \
            f'<pluralLabel>Rexflow {self._label}s</pluralLabel>\n' \
            '<searchLayouts/>\n' \
            '<sharingModel>ReadWrite</sharingModel>\n' \
            '<visibility>Public</visibility>\n'

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
        j = json.dumps(d)
        print(j)

class Profile:
    def __init__(self, name:str):
        self._name = name
        self._fields = []

    def add_field(self, name:str):
        assert len(name) < 41, f'boom! {name} exceeds max length'
        self._fields.append(name)

    def __str__(self):
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' \
            '<Profile xmlns="http://soap.sforce.com/2006/04/metadata">\n' \
                '<userPermissions>\n' \
                    '<enabled>true</enabled>\n' \
                    f'<name>ApiEnabled</name>\n' \
                '</userPermissions>\n' \

        for field in self._fields:
            xml += '<fieldPermissions>\n' \
                f'<field>{field}</field>\n' \
                '<editable>true</editable>\n' \
                '<hidden>false</hidden>\n' \
                '<readable>true</readable>\n' \
            '</fieldPermissions>\n' \

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
</Package>"""

if __name__ == "__main__":
    mode = 2

    sf = Salesforce(
        username='ghester@rexhomes.com.qa1',
        consumer_key='3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk',
        privatekey_file='/root/JWT/server.key',
        domain='test',
    )

    objects = []
    pr = Profile('System Administrator (MFA)')
    wf = Workflow('amorttable-7e262634', ['get_terms','show_table'], {}, '', 0)
    did_pref = wf.did
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
            if mode < 1 and obj.exists(sf):
                print(f'{obj._name} already exists - skipping')
                continue
            objects.append(obj)
            form = task.get_form(None,False)

            for field in form:
                cf = CustomField(field['dataId'], field['label'], 'Text')
                obj.add_field(cf)
                pr.add_field(f'{obj._name}.{cf._name}')

            filex = ZipInfo(f'objects/{obj._name}.object')
            zip_archive.writestr(filex, str(obj))
            print(obj.form_json())
        # now write the Admin profile (updates)
        filex = ZipInfo(f'profiles/{pr._name}.profile')
        zip_archive.writestr(filex, str(pr))

    if len(objects) == 0:
        print("No objects to create - exiting")
        exit(1)

    with open('bogus.zip', 'wb') as f:
        f.write(archive.getbuffer())

    archive.close()

    if mode < 2:
        result = sf.deploy('/opt/rexflow/bogus.zip', True, allowMissingFiles=True, testLevel='NoTestRun')
        asyncId = result['asyncId']
        print(asyncId)
        deployment_finished = False
        successful          = False
        while not deployment_finished:
            result = sf.checkDeployStatus(asyncId, True)
            print(result)
            deployment_finished = result.get('state') in ["Succeeded", "Completed", "Error", "Failed", "SucceededPartial", None]
            successful          = result.get('state') in ["Succeeded", "Completed"]

    # try to insert some data
    # result = sf.Rexflow_amorttable_7e262634_show_table__c.create({'interest__c':'0.030', 'principal__c':'123456.00', 'seller__c':'REX Homes', 'term__c': '30'})

    # modify the form image in etcd to include table and field information about the created objects
