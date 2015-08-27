#!flask/bin/python
__author__ = 'elmira'

from utilities import SQLClient
from flask import Flask, jsonify, abort, make_response, request, render_template
import json

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('animals.html')


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
SELECT DISTINCT l.name, a.name, n.name, s.verb, s.trans, concat(t.name), m.ex
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
    SELECT DISTINCT l.name, a.name, n.name, s.verb, s.trans, concat(t.name), m.ex
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

@app.route('/graph', methods=["GET"])
def graph_making():
    if len(request.args) <= 0:
        abort(404)
        return render_template('movie.html')
    if 'q' in request.args:
        q = request.args["q"]
        a = request.args["a"]
        l = request.args["l"]
        t = request.args["t"]
        print q, a, l, t
        sql_query = make_sql_for_simple_search(a, l, t)
        db = SQLClient(u'animals_db.dtb')
        graph = {"nodes": [], "links": []}
        nodes = []
        for i in db.query(sql_query):
            i = list(i)
            i[5] = ', '.join(sorted(i[5].split(', ')))
            if i[1] not in nodes:
                nodes.append(i[1])
                graph["nodes"].append({u"name":i[1], u'label': u"Animal", u"id":nodes.index(i[1])})
            if i[3] not in nodes:
                nodes.append(i[3])
                graph["nodes"].append({u"name":i[3], u'label': u"Verb", u"id":nodes.index(i[3])})
            if i[5] not in nodes:
                nodes.append(i[5])
                graph["nodes"].append({u"name":i[5], u'label': u"Tag", u"id":nodes.index(i[5])})
            graph["links"].append({u"source":nodes.index(i[1]), u'target': nodes.index(i[3]), u"type": "MAKES_SOUND"})
            if i[5] != '':
                graph["links"].append({u"source":nodes.index(i[3]), u'target': nodes.index(i[5]), u"type": "TAGGED"})
        return json.dumps(graph)


@app.route('/search', methods=['GET'])
def simple_search():
    if len(request.args) <= 0:
        abort(404)
        return render_template('animals.html')
    if 'q' in request.args:
        q = request.args["q"]
        a = request.args["a"]
        l = request.args["l"]
        t = request.args["t"]
        sql_query = make_sql_for_simple_search(a, l, t)
        db = SQLClient(u'animals_db.dtb')
        arr = []
        for i in db.query(sql_query):
            arr.append({u'movie':{u'title':i[2], u'released': i[1], u'language': i[0], u'verb': i[3], u'trans': i[4], u'tag': i[5], u'animal':i[1], u'animal2': i[2], u'ex': i[6]}})
        return json.dumps(arr)
    abort(404)

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
    db = SQLClient(u'animals_db.dtb')
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