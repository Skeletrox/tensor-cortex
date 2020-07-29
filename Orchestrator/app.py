import time
import subprocess
from flask import Flask, request, jsonify
import json
import requests
import random
import asyncio
import aiohttp
import string
from threading import Thread
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

# thread pool
thread_pool = []


def do_awaiting_wrapper(awaitables):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(do_awaiting(awaitables))
    awaitables = []

async def do_awaiting(awaitables):
    global results
    if not results:
        return
    results = await asyncio.gather(*awaitables, return_exceptions=True)

# Random string generator to uniquely identify each docker instance
def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return "".join([random.choice(letters) for i in range(stringLength)])


def join_all_threads():
    global thread_pool
    for t in thread_pool:
        t.join()


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


def demuxRuns(data):
    global tasks, sessions, thread_pool
    if tasks:
        return
    ports = metadata["containers"]
    for i in range(len(ports)):
        session = aiohttp.ClientSession()
        jsonData = {"source": data["sources"][i], "count": data["counts"][i]}
        url = "{}:{}/dry_run".format(DOCKER_URL, ports[i])
        tasks.append(fetchJson(session,url,jsonData,"POST"))
        sessions.append(session)

    task_thread = Thread(target=do_awaiting_wrapper,args=[tasks])
    task_thread.start()
    thread_pool.append(task_thread)


@app.route('/')
def hello():
    return 'Hello World! Visit <a href="https://skeletrox.github.io">skeletrox.github.io</a>!\n'


@app.route('/steps', methods=["POST"])
def demux():
    global tasks
    if len(tasks) > 0:
        return jsonify({
            "error": "tasks still running"
        }), 429

    with open("/var/log/steps.log", "a") as s:
        data = request.json
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # returned = loop.run_until_complete(demuxRuns(data))
        demuxRuns(data)

    return jsonify({
        "success": True,
        "tasks_dispatched": len(tasks),
        "sessions_dispatched": len(sessions)
    }), 200


@app.route('/num_tasks', methods=["GET"])
def getTasks():
    global tasks
    return jsonify({
        "num_tasks": len(tasks)
    }), 200


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
