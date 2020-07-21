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
    
# This is s dynamic "kwarg" wrapper around a dist_nn_class module
# Assumes your class & request to have the method name and the kwargs for any further processin
@app.route('/func', methods=['POST'])
def func():
    r = request.json
    func_name = r.get("func", None)
    func_kwargs = r("kwargs", {})
    if func_name is None:
        return "Missing function name", 400


@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)