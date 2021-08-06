from zipfile import ZipFile
import sys
import subprocess
import datetime

def create_logs(workflow_ids, file_path):
    
    now = datetime.datetime.now()
    zipObj = ZipFile(file_path+'-' + str(now) + '.zip', 'w')
    print("Initializing ZipFile at " + file_path+'-' + str(now))
    for workflow_id in workflow_ids:
        res = subprocess.check_output("kubectl get po -n"+str(workflow_id) + " | awk '{print $1}'", shell=True, text=True)
        res = res.split("\n")
        res = res[1:-1]
        for itm in res:
            dep = itm
            lst = dep.split("-")
            res = ""
            for word in lst[:-2]:
                res += word + "-"
            res = res.strip("-")
            print("Creating " + itm + " logs")
            subprocess.check_output("kubectl logs " + itm + " -n" + workflow_id + " " + res + " >> " + itm + ".log", shell=True, text=True)
            zipObj.write(itm + '.log')
            subprocess.check_output("rm " + itm + ".log", shell=True, text=True)
    print("Closing Zip file")
    zipObj.close()

if len(sys.argv) < 2:
    print("Workflow_id must be specified")
else:
    workflow_id = sys.argv[1]
    file_name = str(workflow_id)
    if len(sys.argv) > 2:
        file_path = sys.argv[2] + "/" + file_name
    else:
        file_path = file_name
    create_logs([workflow_id,'rexflow'],file_path)

