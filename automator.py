import os
import shutil
import subprocess
import logging
import json
from sys import exit, platform

# The directory where all the docker files will be placed
DOCKER_BUILD_DIR = "DOCKERS"

# The docker-compose template string that will be dynamically populated.
template_string = '''
    {service_name}:
        build: {service_folder}
        runtime: nvidia
        ports:
            - "{parent_port}:5000"
        environment:
            - NVIDIA_VISIBLE_DEVICES=all
'''

orchestrator_template = '''
services:
    orchestrator:
        build: ./orchestrator
        ports:
            - "5000:5000"
'''

# The dockerfile template string that will be used to set the host docker's IP
dockerfile_template = '''
FROM cortex_performer:latest    
WORKDIR /code
ENV DOCKER_HOST {dynamic_docker_host}
CMD ["python", "app.py"]
'''

orchestrator_dockerfile = '''
FROM cortex_orchestrator:latest
WORKDIR /code
ENV NUM_PERFORMERS {num_performers}
ENV DOCKER_HOST {dynamic_docker_host}
COPY . .
CMD ["python", "app.py"]
'''


# A helper function to allow for immediate STDOUT from long-running processing
def execute(cmd):
    popen = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


# Number of dockers to bring up
num_dockers = int(input("[+] Enter number of dockers: "))

# The "start" port to anchor from. Dockers interface ports n, n+1, n+2... from the host machine.
start_port = int(input("[+] Enter anchor port: "))

# work_directory can be either the current working directory or a remote directory where the files exist
work_directory = os.getcwd()

# get the docker0 ip address (dynamic on linux only, static on windows)
if platform == 'win32':
    docker0_ip = '192.168.99.100'
else:
    proc = subprocess.check_output(
        "ip -4 addr show docker0 | grep -Po 'inet \K[\d.]+'", shell=True)
    docker0_ip = proc.decode()

print("Docker IP address of host is", docker0_ip)

# Optional build of the orchestrator and service images. Not necessary if images already exist.
build_service = input(
    "Do you wish to build the service docker image? [y/N]: ").upper() == 'Y'
build_orchestrator = input(
    "Do you wish to build the orchestrator docker image? [y/N]: ").upper(
    ) == 'Y'

if build_service:
    os.chdir("{}/PERF_DOCKER/".format(work_directory))
    print("Building target image...")
    for line in execute(["docker", "build", "-t", "cortex_performer", "."]):
        print(line, end="")

if build_orchestrator:
    os.chdir("{}/Orchestrator/".format(work_directory))
    print("\n-------------------\nBuilding orchestrator image...")
    for line in execute(["docker", "build", "-t", "cortex_orchestrator", "."]):
        print(line, end="")

try:
    os.makedirs("{}/{}/".format(work_directory, DOCKER_BUILD_DIR))
except FileExistsError:
    pass

port_list = []

folder_name = "{}/{}".format(work_directory, DOCKER_BUILD_DIR)
try:
    os.makedirs(folder_name)
except FileExistsError:
    pass

try:
    os.makedirs("{}/{}".format(folder_name, "orchestrator"))
except FileExistsError:
    pass

with open("{}/orchestrator/Dockerfile".format(folder_name), 'w+') as df:
    df.write(
        orchestrator_dockerfile.format(
            dynamic_docker_host=docker0_ip, num_performers=num_dockers))

service_folder = "cortex_instance"

try:
    os.makedirs("{}/{}".format(folder_name, service_folder))
except FileExistsError:
    pass

with open("{}/{}/Dockerfile".format(folder_name, service_folder), 'w+') as df:
    df.write(dockerfile_template.format(dynamic_docker_host=docker0_ip))

with open("{}/docker-compose.yml".format(folder_name), 'w+') as d_c:
    d_c.write("version: '2.3'")
    d_c.write(orchestrator_template)
    for i in range(num_dockers):
        service_name = "{}_{}".format(service_folder, i + 1)
        d_c.write(
            template_string.format(
                service_name=service_name,
                service_folder=service_folder,
                parent_port=start_port + i))
        port_list.append(start_port + i)
        print("[*] docker data for instance {} written".format(i + 1))

# The writable dictionary is currently the list of ports
writable_dict = {"containers": port_list}

# Orchestrator needs a configuration file
with open("{}/{}/orchestrator/config.json".format(
        work_directory, DOCKER_BUILD_DIR), "w+") as w:
    w.write(json.dumps(writable_dict))

print("[*] Bringing dockers up...")

os.chdir("{}/{}".format(work_directory, DOCKER_BUILD_DIR))
for line in execute(["docker-compose", "up", "-d"]):
    print(line.strip())
print("[*] Orchestrator and services up. Events logged.".format(i + 1))
