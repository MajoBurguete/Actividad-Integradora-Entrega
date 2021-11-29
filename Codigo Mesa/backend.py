import flask
from flask.json import jsonify
import json
import uuid
from robots_apiladores import Maze, Robot, Box

games = {}

app = flask.Flask(__name__)

@app.route("/games", methods=["POST"])
def create():
    global games
    id = str(uuid.uuid4())
    games[id] = Maze()
    return "ok", 201, {'Location': f"/games/{id}"}


@app.route("/games/<id>", methods=["GET"])
def queryState(id):
    global model
    model = games[id]
    model.step()

    d = {"robots": [], "boxes": [], "stacks": []}

    for a in model.schedule.agents:
        if isinstance(a, Robot):
            d["robots"].append({"id": a.unique_id, "x": a.pos[0], "y": a.pos[1], "hasBox": a.hasBox, "currentBox": a.currentBox.serialize()})
        elif isinstance(a, Box):
            d["boxes"].append({"id": a.unique_id, "x": a.pos[0], "y": a.pos[1], "active": a.active, "isStack": a.isStack})
        else:
            d["stacks"].append({"id": a.unique_id, "x": a.pos[0], "y": a.pos[1], "boxNumber": a.boxNumber})
    
    return jsonify(d)


app.run()