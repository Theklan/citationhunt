import chdb

import flask
import flask_sslify

import os
import collections

def get_db():
    db = getattr(flask.g, '_db', None)
    if db is None:
        db = flask.g._db = chdb.init_db()
    return db

Category = collections.namedtuple('Category', ['id', 'title'])
def get_categories():
    categories = getattr(flask.g, '_categories', None)
    if categories is None:
        cursor = get_db().cursor()
        cursor.execute('''
            SELECT id, title FROM categories ORDER BY title;
        ''')
        categories = flask.g._categories = [Category(*row) for row in cursor]
    return categories

def select_snippet_by_id(id):
    cursor = get_db().cursor()
    cursor.execute('''
        SELECT snippets.snippet, articles.url, articles.title
        FROM snippets, articles WHERE snippets.id = ? AND
        snippets.article_id = articles.page_id;''', (id,))
    ret = cursor.fetchone()
    if ret is None:
        ret = (None, None, None)
    return ret

def select_random_id(category = None):
    cursor = get_db().cursor()

    ret = None
    if category is not None:
        cursor.execute('''
            SELECT snippets.id FROM snippets, categories, articles
            WHERE categories.id = ? AND snippets.article_id = articles.page_id
            AND articles.category_id = categories.id ORDER BY RANDOM()
            LIMIT 1;''', (category,))
        ret = cursor.fetchone()

    if ret is None:
        cursor.execute('''
            SELECT id FROM snippets ORDER BY RANDOM() LIMIT 1;''')
        ret = cursor.fetchone()

    assert ret and len(ret) == 1
    return ret[0]

app = flask.Flask(__name__)
if 'DYNO' in os.environ:
    flask_sslify.SSLify(app)

@app.route('/')
def citation_hunt():
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')

    if id is None:
        id = select_random_id(cat)
        return flask.redirect(
            flask.url_for('citation_hunt', id = id, cat = cat))

    s, u, t = select_snippet_by_id(id)
    if (s, u, t) == (None, None, None):
        flask.abort(404)
    return flask.render_template('index.html',
        snippet = s, url = u, title = t,
        categories = get_categories(), current_category = cat)

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug)
