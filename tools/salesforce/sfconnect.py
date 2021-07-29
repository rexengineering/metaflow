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
from zipfile import ZipFile, ZipInfo
from io import BytesIO
import flowlib.etcd_utils
from flowlib.constants import (
    WorkflowKeys,
    WorkflowInstanceKeys,
)
from uibridge.flowd_api import Workflow, WorkflowTask

class CustomField:
    def __init__(self, name:str, label:str, type:str):
        self._name = f'{name.replace("_","e")}__c'
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

    #    return '<?xml version="1.0" encoding="UTF-8"?>\n' \
    #         '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n' \
    #         f'<fullName>{self._name}__c</fullName>\n' \
    #         '<externalId>false</externalId>\n' \
    #         f'<label>{self._label}</label>\n' \
    #         '<length>180</length>\n' \
    #         '<required>false</required>\n' \
    #         '<trackHistory>false</trackHistory>\n' \
    #         '<trackTrending>false</trackTrending>\n' \
    #         f'<type>{self._type}</type>\n' \
    #         '</CustomField>'

class CustomObject:
    def __init__(self, name:str, label:str):
        # Object Name field can only contain underscores and alphanumeric characters.
        self._name = f'{name.replace("-","").replace("_","e")}__c'
        self._label = label
        self._fields = []

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
            f'<label>Rexflow {self._name.replace("_", " ")}</label>\n' \
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

        pr = Profile('System Administrator (MFA)')
        wf = Workflow('amorttable-7e262634', ['get_terms','show_table'], {}, '', 0)
        task:WorkflowTask
        for task in wf.tasks.values():
            # did/tid combo can't exceed 12 chars
            obj = CustomObject(f'RF{wf.did[0:5]}_{task.tid[0:5]}', wf.did)
            form = task.get_form(None,False)

            for field in form:
                cf = CustomField(field['dataId'], field['label'], 'Text')
                obj.add_field(cf) 
                pr.add_field(f'{obj._name}.{cf._name}')

            filex = ZipInfo(f'objects/{obj._name}.object')
            zip_archive.writestr(filex, str(obj))
        # now write the Admin profile (updates)
        filex = ZipInfo(f'profiles/{pr._name}.profile')
        zip_archive.writestr(filex, str(pr))

    with open('bogus.zip', 'wb') as f:
        f.write(archive.getbuffer())
    
    archive.close()

    # a = CustomObject('BogusCode__c', 'Bogus Code Name')
    # a.add_field(CustomField('BogusCity__c', 'City', 'Text'))
    # a.add_field(CustomField('BogusState__c', 'State', 'Text'))

    # print(a)
