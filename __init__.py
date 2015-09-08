#!flask/bin/python
__author__ = 'elmira'

from utilities import SQLClient, colors, lang_colors
from flask import Flask, jsonify, abort, make_response, request, render_template, url_for, Response
import json
from functools import wraps


app = Flask(__name__, static_folder='./static/', static_path='/static')
# db_name = 'animals_db.dtb' # todo change name!
db_name = '/home/elmira/zvukimu/zvukimu/animals_db.dtb' # todo change name!


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == 'secret'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/fr')
@app.route('/')
def index():
    rule = request.url_rule.rule
    if '/fr' not in rule: templ = 'animals.html'
    else: templ = 'animals_fr.html'
    return render_template(templ)


@app.route('/fr/advanced')
@app.route('/advanced')
def advanced():
    return render_template('advanced.html')

@app.route('/animals')
def an_sel():
    return render_template('animals_sel.html')

@app.route('/languages')
def l_sel():
    return render_template('lang_sel.html')

@app.route('/tags')
def t_sel():
    return render_template('tags_sel.html')

def make_one_query(table, q):
    query = "SELECT id FROM " + table
    if q!= '':
        q = q.split(',')
        query  += ' WHERE '
        query += ' OR '.join(['name="'+i.strip()+'"' for i in q])
    return query

def make_sql_for_simple_search(a, l, t):
    animal_query = make_one_query("Animals", a)
    lang_query = make_one_query("Languages", l)
    tag_query = make_one_query("Tags", t)
    if tag_query == "SELECT id FROM Tags":
        query = """
SELECT DISTINCT l.name, a.name, n.name, s.verb, s.trans, concat(t.name), m.ex, l.id
FROM AnimalNames n INNER JOIN Animals a ON  a.id = n.animal_id
INNER JOIN Languages l ON n.lang_id = l.id
INNER JOIN Sounds s ON (s.lang_id = l.id AND a.id=s.animal_id)
LEFT JOIN Metaphors m ON s.id=m.verb_id
LEFT JOIN Tags t ON m.tag_id=t.id
WHERE l.id IN (""" + lang_query +") AND a.id IN (" + animal_query + """)
GROUP BY s.verb, m.ex
"""
    else:
        query = """
    SELECT DISTINCT l.name, a.name, n.name, s.verb, s.trans, concat(t.name), m.ex, l.id
FROM AnimalNames n INNER JOIN Animals a ON  a.id = n.animal_id
INNER JOIN Languages l ON n.lang_id = l.id
INNER JOIN Sounds s ON (s.lang_id = l.id AND a.id=s.animal_id)
LEFT JOIN Metaphors m ON s.id=m.verb_id
LEFT JOIN Tags t ON m.tag_id=t.id
WHERE l.id IN (""" + lang_query +") AND a.id IN (" + animal_query + """) AND
s.id IN (SELECT verb_id FROM Metaphors WHERE tag_id IN (""" + tag_query + """))
GROUP BY s.verb, m.ex"""
    # print query
    return query

@app.route('/fr/graph', methods=['GET'])
@app.route('/graph', methods=["GET"])
def graph_making():
    if len(request.args) <= 0:
        abort(404)
        return render_template('animals.html')
    if 'q' in request.args:
        q = request.args["q"]
        a = request.args["a"]
        l = request.args["l"]
        t = request.args["t"]
        # print q, a, l, t
        sql_query = make_sql_for_simple_search(a, l, t)
        db = SQLClient(db_name)
        graph = {"nodes": [], "links": []}
        nodes = []
        pairs = {}
        for i in db.query(sql_query):
            i = list(i)
            if i[1] not in pairs:
                pairs[i[1]] = {i[0]}
            else:
                pairs[i[1]].add(i[0])
            if i[5] not in pairs:
                pairs[i[5]] = {i[0]}
            else:
                pairs[i[5]].add(i[0])
            i[5] = ', '.join(sorted(i[5].split(', ')))
            if i[1] not in nodes:
                nodes.append(i[1])
                graph["nodes"].append({u"name":i[1], u'label': u"Animal", u"id":nodes.index(i[1]), "color":"red"})
            if i[3] not in nodes:
                set_color = lang_colors[i[0]]
                nodes.append(i[3])
                graph["nodes"].append({u"name":i[3] + ' (' + i[0] + ')', u'label': u"Verb", u"id":nodes.index(i[3]), "color": set_color})
            if i[5] not in nodes and i[5] != '':
                nodes.append(i[5])
                graph["nodes"].append({u"name":i[5], u'label': u"Tag", u"id":nodes.index(i[5]),"color":"black"})
            graph["links"].append({u"source":nodes.index(i[1]), u'target': nodes.index(i[3]), u"type": "MAKES_SOUND"})
            if i[5] != '':
                graph["links"].append({u"source":nodes.index(i[3]), u'target': nodes.index(i[5]), u"type": "TAGGED"})
        for n in graph['nodes']:
            if n["name"] in pairs:
                n["radius"] = len(pairs[n["name"]])
            else:
                n["radius"] = 0
        #     print n["name"], n["radius"]
        # for i in pairs:
        #     print i, ' '.join(pairs[i])
        return json.dumps(graph)

@app.route('/fr/search', methods=['GET'])
@app.route('/search', methods=['GET'])
def simple_search():
    if len(request.args) <= 0:
        return render_template('animals.html')
    if 'q' in request.args:
        q = request.args["q"]
        a = request.args["a"]
        l = request.args["l"]
        t = request.args["t"]
        sql_query = make_sql_for_simple_search(a, l, t)
        db = SQLClient(db_name)
        arr = []
        for i in db.query(sql_query):
            arr.append({u'data':{u'title':i[2], u'released': i[1], u'language': i[0], u'verb': i[3], u'trans': i[4], u'tag': i[5], u'animal':i[1], u'animal2': i[2], u'ex': i[6]}})
        return json.dumps(arr)
    abort(404)

@app.route('/fr/details/<word>', methods=['GET'])
@app.route('/details/<word>', methods=['GET'])
def get_document(word):
    trans = """SELECT DISTINCT m.trans FROM Sounds s
LEFT JOIN Metaphors m ON s.id=m.verb_id
WHERE s.id IN (SELECT id FROM Sounds WHERE verb='""" + word+ """');"""
    dir = """SELECT DISTINCT d.example, d.trans FROM Sounds s
LEFT JOIN DirectExamples d ON s.id=d.verb_id
WHERE s.id IN (SELECT id FROM Sounds WHERE verb='""" + word+ """');"""
    met = """SELECT DISTINCT m.ex, m.extr, concat(t.name) FROM Sounds s
LEFT JOIN Metaphors m ON s.id=m.verb_id
LEFT JOIN Tags t ON m.tag_id=t.id
WHERE s.id IN (SELECT id FROM Sounds WHERE verb='""" + word+ """') GROUP BY m.ex;"""
    d = {u'verb': word, u"trans": [], u'dir': [], u'met': []}
    db = SQLClient(db_name)
    for i in db.query(trans):
        if i is not None and i is not '': d[u'trans'].append(i)
    for i in db.query(dir):
        if i[0] is not None or i[1] is not None: d[u'dir'].append({u'ex':i[0], u'trans':i[1]})
    for i in db.query(met):
        if i[0] is not None or i[1] is not None: d[u'met'].append({u'ex':i[0], u'trans':i[1], u'tag': i[2]})
    # print d
    return json.dumps(d)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/fr/admin', methods=['GET', 'POST'])
@app.route('/admin', methods=['GET', 'POST'])
@requires_auth
def admin():
    rule = request.url_rule.rule
    templ = 'admin.html' if '/fr/' not in rule else 'admin_fr.html'
    return render_template(templ, loaded_file=False, smth_failed=False)


@app.route('/fr/upload_file', methods=['GET', 'POST'])
@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file_ru():
    rule = request.url_rule.rule
    templ = 'admin.html' if '/fr/' not in rule else 'admin_fr.html'
    # print request.method
    # print request.form  # ImmutableMultiDict([('headers', u'on')])
    # print request.files  # ImmutableMultiDict([('datafile', <FileStorage: u'word.macros.txt' ('text/plain')>)])
    if request.method == 'POST':
        try:
            r = request.form['headers']
            f = request.files['datafile']
            # print f.readlines()[0]
            return render_template(templ, loaded_file=True, smth_failed=False)
        except:
            return render_template(templ, loaded_file=False, smth_failed=True)
    return render_template(templ, loaded_file=False, smth_failed=False)
    # return json.dumps({"result": ''})


# @app.route('/new', methods=['GET', 'POST'])
# def new_doc():
#     if request.method == 'GET':
#         return render_template('index.html')
#     elif request.method == 'POST':
#         print request.form
#         if len(request.form) != 7:
#             return 'Please, fill in all fields'
#         tit = request.form["title"]
#         aut = request.form["author"]
#         uni = request.form["uni"]
#         major = request.form["major"]
#         topic = request.form["topic"]
#         genre = request.form["genre"]
#         text = request.form["text"]
#         docs = es.indices["corpus"]+1
#         # db.insert(u'Participant', students+1, "'"+aut+"'", "'student'", "'"+major+"'", "'"+uni+"'")
#         # db.insert(u'Text', docs, "'"+tit+"'", "'"+topic+"'", "'"+genre+"'", 0, 0, 2015, 2015)
#         doc = make_document([docs, tit, topic, genre, students+1, aut, major, uni], text)
#         es.create(json.dumps(doc))
#         return jsonify({'result': True})

if __name__ == '__main__':
    app.run(debug=True)