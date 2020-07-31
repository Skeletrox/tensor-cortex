import time
import redis
from flask import Flask, jsonify, request
from os import environ
import numpy as np
import subprocess
import json

popen_obj = None

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)


def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.route("/dry_run", methods=["POST"])
def dry_run():
    global popen_obj
    if popen_obj and not popen_obj.poll():
        return jsonify({"response": "still executing previous run"}), 429
    r = request.json
    source = r.get("source", "boy_names")
    count = int(r.get("count", 50))
    proc_string = "python /code/custom_nn.py -s {} -c {}".format(source, count)
    popen_obj = subprocess.Popen(
        proc_string,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True)
    returnable = {"started": True}
    return jsonify(returnable), 200


@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)


@app.route("/getname")
def get_name():
    return jsonify({"ID": environ["ID"]})


@app.route('/setname', methods=["POST"])
def setname():
    environ["ID"] = request.json.get("id", "NULL")
    return jsonify({"ID": environ["ID"]})


@app.route('/poll_result')
def poll_result():
    global popen_obj
    if popen_obj is None:
        return jsonify({"error": "no running task"}), 404
    if popen_obj.poll() is None:
        return jsonify({"complete": False}), 200

    stdout, stderr = popen_obj.communicate()
    with open("names.txt", "r") as names:
        returned_names = json.loads(names.read())
    popen_obj = None

    return jsonify({
        "complete": True,
        "stdout": str(stdout),
        "stderr": str(stderr),
        "result": returned_names
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
