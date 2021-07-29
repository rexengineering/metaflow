from simple_salesforce import Salesforce

if __name__ == "__main__":
    mode = 2
    sf = Salesforce(
        username='ghester@rexhomes.com.qa1',
        consumer_key='3MVG9Eroh42Z9.iXvUyLGLZu3HSJ1y337lFTT1BY8htZ7m7FtBKU9pioaooAT2QJy3.MnktFj.1zZgnOzdPpk',
        privatekey_file='/root/JWT/server.key',
        domain='test',
    )

    # the following does not work ...
    # sf = Salesforce(
    #     username='ghester@rexhomes.com.qa1',
    #     password='C0deF0018374',
    #     security_token='6Cel800D020000008aoW88802000000H35KpYegUksJItspideSuIuy0aSJh6ygmh7gC4gJEuQDLW2Y3dWESWRQj3dVfmv7Wgzu7XQkKOJN',
    #     domain='test',
    # )

    print(sf)

    if mode == 2:
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


