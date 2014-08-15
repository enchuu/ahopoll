#!/usr/bin/env python3

from poll import PollContainer, InvalidInputException, Settings
from flask import Flask, request, redirect
from flask_limiter import Limiter
from werkzeug.contrib.fixers import ProxyFix

polls = PollContainer()
index_page = open('static/index.html').read()
usage_page = open('static/usage.html').read()
resquests_exceeded_page = open('static/requests_exceeded.html').read()
app = Flask(__name__)
limiter = Limiter(app, global_limits=Settings.global_limits)
torlist = set(open('torlist').read().splitlines())

@app.route('/', methods=['GET'])
def index():
        return index_page

@app.route('/submitpoll', methods=['POST'])
@limiter.limit(Settings.create_limits)
def create_poll():
    try:
        form = request.form.get
        log_ip = False if form('dont_log_ip') else True
        hide_results = True if form('hide_results') else False
        title = form('title')
        questions = form('questions')
        description = form('description')
        time_limit = ['0', '0']
        if form('days'):
            time_limit[0] = form('days')
        if form('hours'):
            time_limit[1] = form('hours')
        id = polls.add_poll(title, questions, description, log_ip, time_limit, hide_results)
        return redirect('/vote/' + str(id))
    except InvalidInputException as e:
        return repr(e)

@app.route( '/vote/<id>', methods=['GET'])
def vote(id):
    return polls.get_poll_page(id)

@app.route('/submitvote/<id>', methods=['POST'])
@limiter.limit(Settings.vote_limits)
def submit_vote(id):
    try:
        ip = request.remote_addr
        if ip in torlist:
            raise InvalidInputException("Error: You cannot vote using Tor.")
        form = request.form.getlist
        vote = {}
        for i in range(0, Settings.max_questions):
            opts = form(str(i))
            writeins = form(str(i) + '_writeins')
            if writeins and writeins[0] != '':
                writeins = writeins[0].split('\r\n')
            else:
                writeins = []
            vote[i] = { 'opts': opts, 'writeins': writeins }
        result = polls.add_vote(id, vote, ip)
        return redirect('/results/' + id)
    except InvalidInputException as e:
        return repr(e)

@app.route('/results/<id>', methods=['GET'])
def results(id):
    try:
        return polls.get_results_page(id)
    except InvalidInputException as e:
        return repr(e)

@app.route('/interactive/<id>', methods=['GET'])
def fancy(id):
    try:
        return polls.get_interactive_page(id)
    except InvalidInputException as e:
        return repr(e)

@app.route('/graph/<id>', methods=['GET'])
def graph(id):
    try:
        return polls.get_graph_page(id)
    except InvalidInputException as e:
        return repr(e)

@app.route('/usage', methods=['GET'])
def usage():
    return usage_page

@app.errorhandler(429)
def ratelimit_handler(e):
    return resquests_exceeded_page

if __name__=='__main__':
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.debug = True;
    app.run()
