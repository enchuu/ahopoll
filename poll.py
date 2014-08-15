import re
import time
import random
import kyotocabinet
import json
import string
import bcrypt
from flask import render_template
from flask_limiter import Limiter

class Settings():
    
    database_name = 'db.kch'
    secret_password = '$2a$05$.SISvZQyxxkwEVNnLTgjxu'
    max_options = 250
    max_option_length = 100
    max_questions = 20
    title_limit = 100
    description_limit = 500
    bcrypt_diff = 4
    global_limits = ['10 per 10 seconds', '1000 per day']
    vote_limits = '100 per day;10 per minute;'
    create_limits = '20 per day;5 per minute;'

class InvalidInputException(Exception):

    def __init__(self, message, id=None):
        self.message = message
        self.id = id

    def __repr__(self):
        return render_template('error.html', message=self.message, id=self.id)

class DBContainer():

    does_not_exist = 'This poll at this page does not exist yet.'
    db_error = 'Error opening the database.'

    def __init__(self):
        self.db = kyotocabinet.DB()
        if not self.db.open(Settings.database_name):
            raise InvalidInputException(PollContainer.db_error)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.db.close()

    def set_obj(self, key, value):
        if not self.db.set(key, json.dumps(value)):
            raise InvalidInputException(DBContainer.does_not_exist)

    def get_obj(self, key):
        return json.loads(self.get(key).decode())

    def get(self, key):
        val = self.db.get(key)
        if not val:
            raise InvalidInputException(DBContainer.does_not_exist)
        return val
    
    def check(self, key):
        val = self.db.get(key)
        return val

class PollContainer():

    already_voted = 'Error: You have already voted in this poll.'

    def add_poll(self, title, questions, description, log_ip=True, time_limit=None, hide_results=False):
        with DBContainer() as db:
            id = PollContainer.random_string(8)
            while db.check(id):
                id = PollContainer.random_string(8)
            poll = Poll.make_poll(id, title, questions, description, log_ip, time_limit, hide_results)
            db.set_obj(id, poll)
            db.set_obj(id + '-votes', [])
            db.set_obj(id + '-ips', [])
            return id

    def add_vote(self, id, vote, ip=None):
        with DBContainer() as db:
            poll = db.get_obj(id)
            if poll['log_ip']:
                ips = db.get_obj(id + '-ips')
                ip_hash = PollContainer.check_ip(poll, ip, ips)
            new_vote = Poll.add_vote(poll, vote, ip)
            votes = db.get_obj(id + '-votes')
            votes.append(new_vote)
            db.set_obj(id + '-votes', votes)
            db.set_obj(id, poll)
            if poll['log_ip']:
                ips.append(ip_hash)
                db.set_obj(id + '-ips', ips)

    def get_results_page(self, id):
        with DBContainer() as db:
            poll = db.get_obj(id)
            return Poll.make_results_page(poll)

    def get_interactive_page(self, id):
        with DBContainer() as db:
            poll = db.get_obj(id)
            votes = db.get(id + '-votes').decode()
            return Poll.make_interactive_results_page(poll, votes)

    def get_graph_page(self, id):
        with DBContainer() as db:
            poll = db.get_obj(id)
            votes = db.get(id + '-votes').decode()
            return Poll.make_graph_page(poll, votes)

    def get_poll_page(self, id):
        with DBContainer() as db:
            poll = db.get_obj(id)
            return Poll.make_poll_page(poll)

    def check_ip(poll, ip, ips):
        salt = poll['salt']
        hashed = bcrypt.hashpw((ip + Settings.secret_password).encode(), salt.encode()).decode()
        if hashed in ips:
            raise InvalidInputException(PollContainer.already_voted)
        return hashed

    def random_string(length):
        return ''.join(random.choice(string.ascii_lowercase + string.digits) \
                  for i in range(length))


class Votes():

    def make_vote(vote):
        return {'time': time.time(), 'vote': vote}


class Question():

    csn = re.compile('^[0-9]+,[0-9]+$')
    num = re.compile('^[0-9]+$')
    same_opts = 'Error: You cannot have both the min and max amount of options be {}\
                     for question {}.'
    too_few_opts = 'Error: Question {} does not have enough options.'
    max_less_min = 'Error: Question {} has max votes less than min votes.'
    wrong_num_opts = 'Error: Question {} does not have the proper number of options selected.'
    invalid_opt = 'Error: Invalid option entered for question {}.'
    no_write_in = 'Error: You attempted to enter write-in options for a question without them.'
    too_many_opts = 'Error: Question {} has too many options. The max amount of options \
                     per question is ' + str(Settings.max_options) + '.'
    too_long_opt = 'Error: One of your options for question {} is longer than \
                    the limit of ' + str(Settings.max_option_length) + ' characters.'

    def make_question(s, i):
        question = {}
        s = s.strip()
        lines = list(map(lambda s: s.strip(), s.splitlines()))
        if len(lines) < 2:
            raise InvalidInputException(Question.too_few_opts.format(i))
        question['question'] = lines[0]
        question['writein'] = lines[-1] == '*'
        question['minopts'], question['maxopts'], option_start = \
                Question.get_option_counts(lines[1])
        option_end = len(lines) - (1 if question['writein'] else 0)
        if question['maxopts'] < question['minopts']:
            raise InvalidInputException(Question.max_less_min.format(i))
        question['options'] = Question.validate_options(lines[option_start:option_end], i)
        opts = len(question['options'])
        if question['minopts'] == question['maxopts']:
            if question['minopts'] == 0:
                raise InvalidInputException(Question.same_opts.format(0, i))
            if  question['minopts'] == opts:
                raise InvalidInputException(Question.same_opts.format(question['minopts'], i))
        if opts > 250:
            raise InvalidInputException(Question.too_many_opts.format(i))
        if not question['writein']:
            if opts < question['maxopts']:
                raise InvalidInputException(Question.too_few_opts.format(i))
        question['votes'] = list(map(lambda option: \
                {'option': option, 'votes': 0}, question['options']))
        question['range'] = Question.get_formatted_range(question)
        return question

    def validate(question, vote, i, writeins=[]):
        Question.validate_options(writeins, i)
        if not question['writein'] and writeins:
            raise InvalidInputException(Question.no_write_in.format(i))
        if len(question['options']) + len(writeins) > 250:
            raise InvalidInputException(Question.too_many_opts.format(i))
        opts = len(vote) + len(writeins)
        for o in vote:
            if not o.isdigit():
                raise InvalidInputException(Question.invalid_opt.format(i))
            o = int(o)
            if o < 0 or o >= len(question['options']):
                raise InvalidInputException(Question.invalid_opt.format(i))
        if opts < question['minopts'] or opts > question['maxopts']:
            raise InvalidInputException(Question.wrong_num_opts.format(i))

    def add_vote(question, vote, i, writeins=[]):
        Question.validate(question, vote, i, writeins)
        for o in vote:
            question['votes'][int(o)]['votes'] += 1
        if question['writein']:
            question['votes'].extend(map(lambda option: \
                    {'option': option, 'votes': 1}, writeins))
            question['options'].extend(writeins) 

    def get_formatted_range(question):
        if question['minopts'] == question['maxopts']:
            return str(question['minopts'])
        return '{}-{}'.format(question['minopts'], question['maxopts'])

    def validate_options(options, i):
        for o in options:
            if len(o) > Settings.max_option_length:
                raise InvalidInputException(Question.too_long_opt.format(i))
        return options

    def get_option_counts(line):
        if Question.csn.match(line):
            limits = list(map(int, line.split(',')))
            minopts = limits[0]
            maxopts = limits[1]
            option_start = 2
        elif Question.num.match(line):
            minopts = int(line)
            maxopts = int(line)
            option_start = 2
        else:
            minopts = 1
            maxopts = 1
            option_start = 1
        return (minopts, maxopts, option_start)


class Poll():

    no_title = 'Error: No title was entered.' 
    not_available = 'Error: The results of this poll are not available yet.'
    no_questions = 'Error: No questions were entered.'
    too_many_questions = 'Error: You entered more than {} questions.'\
                    .format(Settings.max_questions)
    invalid_title = 'Error: The title must be shorter than {} characters.'\
                    .format(Settings.title_limit)
    invalid_description = 'Error: The description must be shorther than {} characters.'\
                    .format(Settings.description_limit)
    time_expired = 'Error: The time limit for this poll has already expired.'
    invalid_time_limit = 'Error: The time limit was unable to be parsed. \
            Hours must be an integer between 0 and 23, and days must be an integer \
            between 0 and 365.'

    def make_poll(id, title, questions, description, log_ip=True, time_limit=None, hide_results=False):
        if not title:
            raise InvalidInputException(Poll.no_title)
        if not questions or not questions.strip():
            raise InvalidInputException(Poll.no_questions)
        if len(title) > Settings.title_limit:
            raise InvalidInputException(Poll.invalid_title)
        if len(description) > Settings.description_limit:
            raise InvalidInputException(Poll.invalid_description)
        poll = {}
        poll['id'] = id
        poll['log_ip'] = log_ip
        poll['title'] = title
        poll['description'] = description
        poll['creation_time'] = time.time()
        poll['hide_results'] = hide_results
        question_strings = questions.strip().split('\r\n\r\n')
        if len(question_strings) > 20:
            raise InvalidInputException(too_many_questions)
        poll['questions'] = [Question.make_question(s, n + 1) for (n, s) in \
                          enumerate(question_strings)]
        poll['vote_count'] = 0
        poll['time_limit'] = Poll.parse_time(time_limit)
        poll['salt'] = bcrypt.gensalt(Settings.bcrypt_diff).decode()
        return poll

    def add_vote(poll, vote, ip = None):
        try:
            hash = Poll.check_time(poll)
            new_vote = {}
            for i, question in enumerate(poll['questions']):
                v = vote[i]
                Question.add_vote(question, v['opts'], i + 1, v['writeins'])
                new_opts = range(len(question['options']) - len(v['writeins']), \
                           len(question['options']))
                new_vote[i] = v['opts'] + list(map(str, new_opts))
            poll['vote_count'] += 1
            return Votes.make_vote(new_vote)
        except InvalidInputException as e:
            raise InvalidInputException(e.message, poll['id'])

    def make_poll_page(poll):
        return render_template('poll.html', poll = poll
                                , id=poll['id'], time_left=Poll.fmt_time_left(poll))

    def make_results_page(poll):
        if poll['hide_results']:
            if time.time() < poll['time_limit']:
                raise InvalidInputException(Poll.not_available, poll['id'])
        return render_template('results.html', poll=poll\
                                , id=poll['id'], time_left=Poll.fmt_time_left(poll))
        
    def make_interactive_results_page(poll, votes):
        if poll['hide_results']:
            if time.time() < poll['time_limit']:
                raise InvalidInputException(Poll.not_available, poll['id'])
        return render_template('interactive.html', votes = votes, poll = poll
                                , id=poll['id'], time_left=Poll.fmt_time_left(poll))

    def make_graph_page(poll, votes):
        if poll['hide_results']:
            if time.time() < poll['time_limit']:
                raise InvalidInputException(Poll.not_available, poll['id'])
        return render_template('graph.html', votes = votes, poll = poll
                                , id=poll['id'], time_left=Poll.fmt_time_left(poll))

    def check_time(poll):
        if poll.get('time_limit'):
            if time.time() > poll['time_limit']:
                raise InvalidInputException(Poll.time_expired)

    def parse_time(time_limit):
        try:
            days = int(time_limit[0])
            hours = int(time_limit[1])
            if days > 365 or hours > 24:
                raise InvalidInputException(Poll.invalid_time_limit)
            time_to_end = (days * 24 + hours) * 3600
            if time_to_end == 0:
                return 0
            return time.time() + time_to_end
        except ValueError:
            raise InvalidInputException(Poll.invalid_time_limit)

    def fmt_time_left(poll):
        diff = poll['time_limit'] - time.time()
        if diff < 0:
            return None
        minutes = int(diff / 60) % 60
        hours = int(diff / 3600) % 24
        days = int(diff / 3600 / 24)
        s = ''
        if days:
            s += str(days) + (' day ' if days == 1 else ' days ')
        if hours:
            s += str(hours) + (' hour ' if hours == 1 else ' hours ')
        if minutes or s == '':
            s += str(minutes) + (' minute ' if minutes == 1 else ' minutes ')
        return s.strip()
