import urllib2
import json
from os import environ
from flask import Flask, render_template

REGISTRY_URL = environ.get("REGISTRY_URL", "http://localhost:5000") + "/v2"
DEBUG = environ.get("DEBUG", True)

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = DEBUG

@app.route("/")
def index():
    result = _query("/_catalog")
    return render_template('index.html', repos=result['repositories'])

@app.route("/images/<repo>")
@app.route("/images/<repo>/<image>")
def images(repo, image=None):
    if None == image:
        result = _query("/%s/tags/list" % repo)
    else:
        result = _query("/%s/%s/tags/list" % (repo, image))
    return render_template('images.html', name=result['name'], tags=result['tags'])

@app.route("/image/<repo>/<tag>/manifests")
@app.route("/image/<repo>/<image>/<tag>/manifests")
def manifests(repo, tag, image=None):
    if None == image:
        result = _query("/%s/manifests/%s" % (repo, tag))
    else:
        result = _query("/%s/%s/manifests/%s" % (repo, image, tag))

    layers = []
    for history in result['history']:
        data = json.loads(history['v1Compatibility'])
        if 'Size' in data:
            size = data['Size']
        else:
            size = None
        layers.append({
            'id': data['id'],
            'created': data['created'],
            'command': data['container_config']['Cmd'][2],
            'size': size})
    return render_template('manifests.html', name=result['name'], tag=result['tag'], layers=layers)

def _query(path):
    if DEBUG:
        print "querying:", path
    try:
        response = urllib2.urlopen(REGISTRY_URL + path)
        result = json.loads(response.read())
    except Exception as e:
        if DEBUG:
            print e, "Path:", path
        result = ''
    return result

if __name__ == "__main__":
    print "debug:", DEBUG
    app.run(host='0.0.0.0', debug=DEBUG, port=8080)
