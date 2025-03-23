from flask import Flask, redirect
import socket
import os
import time
import subprocess

app = Flask(__name__)

def get_host_info():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return f"Current Instance IP: {ip}<br>Hostname: {hostname}"

@app.route('/')
def info():
    return get_host_info()

def get_vm_ip(max_attempts=5, delay=1):
    attempts = 0
    while attempts < max_attempts:
        print(attempts)
        if os.path.exists("vm_ip.txt"):
            print('Path Exists')
            with open("vm_ip.txt") as f:
                print('Opened File')
                ip = f.read()
                return ip
        time.sleep(delay)
        attempts += 1
    return None

def ping_server(ip):
    try:
        output = subprocess.check_output(['ping', '-c', '4', ip]).decode('utf-8')
        with open('ping_output.txt', 'w') as f:
            f.write(output)
        return output
    except subprocess.CalledProcessError as e:
        return f"Error pinging server: {e}"

@app.route('/app')
def main_app():
    vm_ip = get_vm_ip()
    print('Request' + str(vm_ip))
    if vm_ip:
        print('IP'+vm_ip)
        # Redirect traffic to the GCP VM
        return redirect(f"http://{vm_ip}:5000")
    return "Local application content"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
