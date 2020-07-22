import time
import redis
from flask import Flask, jsonify, request
from custom_nn import KerasModel, start_flag, done_flag
from os import environ
import numpy as np

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
    r = request.json
    source = r.get("source", "boy_names")
    count = int(r.get("count", 50))
    model = KerasModel(source, count)
    model.load_data()
    model.create_model()
    model.train_model()
    returnable = {"sample": model.return_names()}
    return jsonify(returnable), 200


@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)


@app.route("/getname")
def get_name():
    return jsonify({"ID": environ["TORCS_ID"]})


@app.route('/setname', methods=["POST"])
def setname():
    environ["TORCS_ID"] = request.json.get("id", "NULL")
    return jsonify({"ID": environ["TORCS_ID"]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
