import urllib2
import json
import math
import re
from datetime import datetime
from os import environ
from flask import Flask, request, render_template, redirect, url_for

REGISTRY_URL = environ.get("REGISTRY_URL", "http://172.17.0.1:5000")
DEBUG = environ.get("DEBUG", False)

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = DEBUG

app.jinja_env.globals['registry'] = REGISTRY_URL[REGISTRY_URL.find("//")+2:]

@app.route("/")
def index():
    result = _query("/_catalog")
    repos = []
    image = request.args.get('image')
    print image
    for repo in result['repositories']:
        if None != image and image not in repo:
            continue
        tags = _query("/%s/tags/list" % repo)
        repos.append({"name": repo, "tags": len(tags['tags'])})
    return render_template('index.html', repos=repos)

@app.route("/images/<repo>")
@app.route("/images/<repo>/<image>")
def images(repo, image=None):
    if None == image:
        result = _query("/%s/tags/list" % repo)
    else:
        result = _query("/%s/%s/tags/list" % (repo, image))

    tags = []
    for tag in result["tags"]:
        manifests = _manifests(repo, tag, image)
        tags.append({
            "tag": tag,
            "tagId": manifests["tagId"],
            "created": manifests["created"],
            "layersCount": manifests["layersCount"],
            "size": manifests["size"],
        })
    info = request.args.get('info')
    error = request.args.get('error')
    return render_template('images.html',
                           name=result['name'],
                           tags=tags,
                           info=info,
                           error=error)

@app.route("/delete/<repo>/<tag>")
@app.route("/delete/<repo>/<image>/<tag>")
def delete(repo, tag, image=None):
    if None == image:
        result = _query("/%s/manifests/%s" % (repo, tag))
        digest = result["digest"]
        url = REGISTRY_URL + "/v2/%s/manifests/%s" % (repo, digest)
    else:
        result = _query("/%s/%s/manifests/%s" % (repo, image, tag))
        digest = result["digest"]
        url = REGISTRY_URL + "/v2/%s/%s/manifests/%s" % (repo, image, digest)

    try:
        req = urllib2.Request(url)
        req.get_method = lambda: 'DELETE'
        res = urllib2.urlopen(req)

        content = json.loads(res.read())
        print content
        image_full_name = (repo + ":" + tag) if Node == image else (repo + "/" +image + ":" + tag)
        info = "Image: " + image_full_name + " deleted."
        error = None
    except urllib2.HTTPError:
        error = "Operation not supported yet by registry."
        info = None

    return redirect(url_for("images",
                            repo=repo,
                            image=image,
                            info=info,
                            error=error))

@app.route("/manifests/<repo>/<tag>")
@app.route("/manifests/<repo>/<image>/<tag>")
def manifests(repo, tag, image=None):
    result = _manifests(repo, tag, image)
    return render_template('manifests.html',
                           name=result['name'],
                           tag=result['tag'],
                           tagId=result["tagId"],
                           digest=result["digest"],
                           totalSize=result["size"],
                           layers=result["layers"])

def _manifests(repo, tag, image=None):
    if None == image:
        result = _query("/%s/manifests/%s" % (repo, tag))
    else:
        result = _query("/%s/%s/manifests/%s" % (repo, image, tag))

    layers = []
    total_size = 0
    for history in result['history']:
        raw_data = history['v1Compatibility']
        raw_data = re.sub(r'\\t', '  ', raw_data)
        raw_data = re.sub('\s+\\\\u0026\\\\u0026', ' \\\\\\\\<br/>  \\\\u0026\\\\u0026', raw_data)
        raw_data = re.sub('\s{5,}', ' \\\\\\\\<br/>    ', raw_data)
        data = json.loads(raw_data)
        if 'Size' in data:
            size = int(data['Size'])
            total_size += size
        else:
            size = 0
        layers.append({
            'id': data['id'],
            'created': data['created'],
            'command': data['container_config']['Cmd'][2],
            'size': _filesizeformat(size)})
    layers.sort(key=_getCreated)
    image_id = layers[-1]["id"]
    created = layers[-1]["created"][0:19]
    image_created = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S").strftime("%Y %b %d %H:%M:%S")

    return {
        "name": result["name"],
        "tag": tag,
        "tagId": image_id,
        "created": image_created,
        "size": _filesizeformat(total_size),
        "digest": result["digest"],
        "layers": layers,
        "layersCount": len(layers)
    }

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
                           title="Page Not Found",
                           message="Maybe an UFO took it away..."), 404

@app.errorhandler(500)
def internal_server_error(e):
    if DEBUG:
        print e
    return render_template('error.html',
                           title="Error",
                           message="Something went wrong, and the engineer is napping..."), 500

@app.errorhandler(urllib2.URLError)
def url_error(e):
    if DEBUG:
        print e
    return render_template('error.html',
                           title="Registry Not Available",
                           message="The registry is not available: " + REGISTRY_URL), 503

def _query(path):
    if DEBUG:
        print "querying:", REGISTRY_URL + path
    response = urllib2.urlopen(REGISTRY_URL + "/v2" + path)
    result = json.loads(response.read())
    if "Docker-Content-Digest" in response.headers:
        result["digest"] = response.headers["Docker-Content-Digest"]
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
    app.run(host='0.0.0.0', debug=DEBUG, port=8080)
