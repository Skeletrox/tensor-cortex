import time
import subprocess
from flask import Flask, request, jsonify
import json
import requests
import random
import asyncio
import aiohttp
import string
from os import environ
from sys import exit

app = Flask(__name__)

metadata = None
with open('./config.json') as config:
    metadata = json.loads(config.read())

DOCKER_URL = "http://{}".format(environ["DOCKER_HOST"])

envs = None
results = None

# List of executing tasks. New tasks will only be added to this when empty
tasks = []

# List of sessions pertaining to above tasks. Similar constraints apply.
sessions = []

# any results
results = []


# Random string generator to uniquely identify each docker instance
def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return "".join([random.choice(letters) for i in range(stringLength)])


async def fetchJson(session, url, jsonData=None, method=None):
    if method == "POST":
        async with session.post(url, json=jsonData) as response:
            return await response.text()
    else:
        async with session.get(url) as response:
            return await response.text()


async def rollCallAsync():
    rc_tasks = []
    rc_sessions = []
    ports = metadata["containers"]
    for i in range(len(ports)):
        session = aiohttp.ClientSession()
        url = "{}:{}/getname".format(DOCKER_URL, ports[i])
        rc_tasks.append(fetchJson(session, url))
        rc_sessions.append(session)
    res = await asyncio.gather(*rc_tasks, return_exceptions=True)
    for session in rc_sessions:
        await session.close()
    return res


async def demuxRuns(data):
    ports = metadata["containers"]
    tasks = []
    sessions = []
    for i in range(len(ports)):
        session = aiohttp.ClientSession()
        jsonData = {"source": data["sources"][i], "count": data["counts"][i]}
        url = "{}:{}/dry_run".format(DOCKER_URL, ports[i])
        tasks.append(fetchJson(session, url, jsonData, "POST"))
        sessions.append(session)
    res = await asyncio.gather(*tasks, return_exceptions=True)
    for session in sessions:
        await session.close()
    return res


async def demuxPolls():
    ports = metadata["containers"]
    tasks = []
    sessions = []
    for i in range(len(ports)):
        session = aiohttp.ClientSession()
        url = "{}:{}/poll_result".format(DOCKER_URL, ports[i])
        tasks.append(fetchJson(session, url))
        sessions.append(session)
    res = await asyncio.gather(*tasks, return_exceptions=True)
    for session in sessions:
        await session.close()
    return res


@app.route('/')
def hello():
    return 'Hello World! Visit <a href="https://skeletrox.github.io">skeletrox.github.io</a>!\n'


@app.route('/steps', methods=["POST"])
def demux():
    returnable = []
    with open("/var/log/steps.log", "a") as s:
        data = request.json
        returnable = []
        loop = asyncio.new_event_loop()
        returned = loop.run_until_complete(demuxRuns(data))
        for r in returned:
            try:
                returnable.append(json.loads(r))
            except Exception as e:
                s.write(str(e) + "\n")

    return jsonify({"responses": returnable})


@app.route('/poll_results')
def demux_polls():
    returnable = []
    with open("/var/log/polls.log", "w") as p:
        loop = asyncio.new_event_loop()
        returned = loop.run_until_complete(demuxPolls())
        for r in returned:
            # This is a stringified JSON response
            value = json.loads(r)
            # If the execution is complete and there is a value
            # Complete will be set to True
            if value.get("complete", False):
                # Results exist
                returned_list = value.get("result", None)
                returnable.append(returned_list)
            else:
                # Oops no
                returnable.append(value)
        p.write(str(returned))
    return jsonify({"returned": returnable})


@app.route('/num_tasks', methods=["GET"])
def getTasks():
    global tasks
    return jsonify({"num_tasks": len(tasks)}), 200


@app.route('/init')
def initWorkers():
    global envs
    envs = []
    ports = metadata["containers"]
    returnable = {}

    for i in range(len(ports)):
        value = randomString()
        r = requests.post(
            url="{}:{}/setname".format(DOCKER_URL, ports[i]),
            json={
                "id": value
            })
        returnable[value] = r.json()
    return jsonify({"responses": returnable}), 200


@app.route('/rollcall')
def rollCall():
    with open('/var/log/rollcall.log', 'a') as r:
        loop = asyncio.new_event_loop()
        returnable = loop.run_until_complete(rollCallAsync())
    return jsonify({"responses": [json.loads(r) for r in returnable]}), 200


@app.route('/dry_runs', methods=["POST"])
def dry_runs():
    ports = metadata["containers"]
    returnable = {}
    for i in range(len(ports)):
        r = requests.get(url="{}:{}/dry_run".format(DOCKER_URL, ports[i]))
        returnable[i] = r.json()

    return jsonify({"responses": returnable}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
