import time
import redis
from flask import Flask, jsonify, request
from custom_nn import KerasModel, start_flag, done_flag
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


@app.route("/dry_run", methods=['POST'])
def dry_run():
    r = request.json
    source = r.get("source", "boy_names")
    count = int(r.get("count", 50))
    model = KerasModel(source, count)
    model.load_data()
    model.create_model()
    model.train_model()
    returnable = {
        "sample": model.return_names()
    }
    return jsonify(returnable), 200


@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)