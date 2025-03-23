import os
import time
import psutil
import json
import subprocess
from google.cloud import compute_v1
import threading

PROJECT_ID = "assignment-3-454613"
ZONE = "us-central1-a"
VM_NAME = "auto-scale-vm"
CPU_THRESHOLD = 75
COOLDOWN = 300  # 5 minutes cooldown

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def vm_exists():
    cmd = [
        "gcloud", "compute", "instances", "list",
        "--filter=name:" + VM_NAME,
        "--format=json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return len(json.loads(result.stdout)) > 0

def create_vm():
    app_content = '''from flask import Flask\nimport socket\n\napp = Flask(__name__)\n\n@app.route('/')\ndef info():\n\thostname = socket.gethostname()\n\tip = socket.gethostbyname(hostname)\n\treturn f"VM IP: {ip}<br>Hostname: {hostname}"\n\nif __name__ == '__main__':\n\tapp.run(host='0.0.0.0', port=5000)'''

    startup_script = f'''#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip
pip3 install flask

echo "{app_content}" > app.py

python3 app.py
'''
    
    client = compute_v1.InstancesClient()
    config = {
        "name": VM_NAME,
        "machine_type": f"zones/{ZONE}/machineTypes/n1-standard-1",
        "disks": [{
            "boot": True,
            "initialize_params": {
                "source_image": "projects/debian-cloud/global/images/family/debian-11"
            }
        }],
        "network_interfaces": [{
            "access_configs": [{"type": "ONE_TO_ONE_NAT"}]
        }],
        "metadata": {
            "items": [{
                "key": "startup-script",
                "value": startup_script
            }]
        },
        "tags": {
            "items": ["flask-server"]
        }
    }
    
    operation = client.insert(project=PROJECT_ID, zone=ZONE, instance_resource=config)
    operation.result()
    
    # Wait for the VM to be fully created and running
    while True:
        instance = client.get(project=PROJECT_ID, zone=ZONE, instance=VM_NAME)
        if instance.status == 'RUNNING':
            break
        time.sleep(10)  # Wait 10 seconds before checking again
    
    # Get public IP
    return instance.network_interfaces[0].access_configs[0].nat_i_p

def log_cpu_usage():
    while True:
        cpu = psutil.cpu_percent()
        print(f"Current CPU: {cpu}% at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(5)

def manage_scaling():
    last_trigger = 0
    current_vm_ip = None

    while True:
        cpu = get_cpu_usage()
        print(f"CPU usage check: {cpu}%")
        
        vm_exists_result = vm_exists()
        print(f"VM exists: {vm_exists_result}")
        
        if cpu > CPU_THRESHOLD and not vm_exists_result:
            if time.time() - last_trigger > COOLDOWN:
                print("Creating VM...")
                current_vm_ip = create_vm()
                with open("vm_ip.txt", "w") as f:
                    f.write(current_vm_ip)
                last_trigger = time.time()
                print(f"VM created with IP: {current_vm_ip}")
        time.sleep(10)

if __name__ == "__main__":
    cpu_logger = threading.Thread(target=log_cpu_usage)
    cpu_logger.daemon = True  
    cpu_logger.start()
    
    manage_scaling()
