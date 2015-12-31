import urllib2, httplib
import json
import math
from os import environ
from flask import Flask, render_template, redirect

REGISTRY_URL = environ.get("REGISTRY_URL", "http://localhost:5000")
DEBUG = environ.get("DEBUG", True)

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = DEBUG

app.jinja_env.globals['registry'] = REGISTRY_URL

@app.route("/")
def index():
    result = _query("/_catalog")
    return render_template('index.html', repos=result['repositories'])

@app.route("/images/<repo>")
@app.route("/images/<repo>/<image>")
def images(repo, image=None):
    if DEBUG:
        print "repo:", repo, ", image:", image
    if None == image:
        result = _query("/%s/tags/list" % repo)
    else:
        result = _query("/%s/%s/tags/list" % (repo, image))
    if DEBUG:
        print result
    return render_template('images.html', name=result['name'], tags=result['tags'])


@app.route("/delete/<repo>/<tag>")
@app.route("/delete/<repo>/<image>/<tag>")
def delete(repo, tag, image=None):
    conn = httplib.HTTPConnection("localhost:5000")
    if None == image:
        result = _query("/%s/manifests/%s" % (repo, tag))
        digest = result["digest"]
        conn.request("DELETE", "/v2/%s/manifests/%s" % (repo, digest))
    else:
        result = _query("/%s/%s/manifests/%s" % (repo, image, tag))
        digest = result["digest"]
        conn.request("DELETE", "/v2/%s/%s/manifests/%s" % (repo, image, digest))

    response = conn.getresponse()
    content = response.read()
    print content
    return redirect("/images/" + repo)

@app.route("/manifests/<repo>/<tag>")
@app.route("/manifests/<repo>/<image>/<tag>")
def manifests(repo, tag, image=None):
    if None == image:
        result = _query("/%s/manifests/%s" % (repo, tag))
    else:
        result = _query("/%s/%s/manifests/%s" % (repo, image, tag))

    layers = []
    totalSize = 0
    for history in result['history']:
        data = json.loads(history['v1Compatibility'])
        if 'Size' in data:
            size = int(data['Size'])
            totalSize += size
        else:
            size = 0
        layers.append({
            'id': data['id'],
            'created': data['created'],
            'command': data['container_config']['Cmd'][2],
            'size': _filesizeformat(size)})
    layers.sort(key=_getCreated)
    id=layers[0]["id"]
    return render_template('manifests.html',
                           name=result['name'],
                           tag=result['tag'],
                           id=id,
                           digest=result["digest"],
                           totalSize=_filesizeformat(totalSize),
                           layers=layers)

def _query(path):
    if DEBUG:
        print "querying:", REGISTRY_URL + path
    try:
        response = urllib2.urlopen(REGISTRY_URL + "/v2" + path)
        result = json.loads(response.read())
        if "Docker-Content-Digest" in response.headers:
            result["digest"] = response.headers["Docker-Content-Digest"]
    except Exception as e:
        if DEBUG:
            print e, "Path:", path
        result = ''
    return result

def _getCreated(data):
    return data["created"]

def _filesizeformat(bytes, precision=2):
    bytes = int(bytes)
    if bytes is 0:
        return '0 byte'
    log = math.floor(math.log(bytes, 1024))
    return "%.*f%s" % (
        precision,
        bytes / math.pow(1024, log),
        [' bytes', 'K', 'M', 'G', 'T','P', 'E', 'Z', 'Y']
        [int(log)]
    )

if __name__ == "__main__":
    print "debug:", DEBUG
    app.run(host='0.0.0.0', debug=DEBUG, port=8080)
