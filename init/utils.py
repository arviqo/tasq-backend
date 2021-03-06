# Stdlib imports
import json

from random import choice
from datetime import datetime

# Core Flask imports
from flask import current_app, render_template

# Third-party app imports
import jwt
import boto3
import hashlib

from flask_mail import Message

# Imports from your apps
from init.mail_init import mail


def generate_jwt_token(user_id):
    iat = datetime.utcnow()
    return jwt.encode(
        {
            'user_id': user_id,
            'iat': iat,
            'exp':
                (iat + current_app.config.get('JWT_EXPIRATION_DELTA')),
            'nbf':
                (iat + current_app.config.get('JWT_NOT_BEFORE_DELTA')),
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    ).decode('utf-8')


def parse_json_to_object(obj, data_json, fields=(), exclude=()):
    _fields = set(data_json.keys())

    if exclude:
        _fields = _fields - set(exclude)

    if fields:
        _fields = set(fields) & _fields

    _fields -= set(['id'])

    for field in _fields:
        value = data_json[field]
        setattr(obj, field, value)


def generate_password(length=16, use_special_chars=False):
    charsets = [
        'abcdefghijklmnopqrstuvwxyz',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '0123456789'
    ]
    if use_special_chars:
        charsets += ['^!\$%&/()=?{[]}+~#-_.:,;<>|\\']

    pwd = []
    charset = choice(charsets)
    while len(pwd) < length:
        pwd.append(choice(charset))
        charset = choice(list(set(charsets) - {charset}))
    return "".join(pwd)


def make_password_hash(password):
    return hashlib.md5(
        password.join(
            current_app.config['SECRET_KEY']
        ).encode('utf-8')
    ).hexdigest()


def send_email(template='', params={}, subject='', recipients=[]):
    """
        relative path to template from templates folder,
            for instance forgotten_password.html
        :param template: string, template name
        :param params: object, template data
        :param subject: string, email subject
        :param recipients: array, list of recipients
    """

    # params.update({
    #     "EMAIL_TEMPLATES_IMAGES":
    #         current_app.config['EMAIL_TEMPLATES_IMAGES']
    # })

    msg_html = render_template(
        template,
        **params
    )

    if current_app.config['DEBUG']:
        msg = Message(subject, recipients=recipients)
        msg.html = msg_html
        try:
            mail.send(msg)
        except Exception as e:
            print(e)
        return

    data = {
        "html": msg_html,
        "subject": subject,
        "params": params,
        "recipients": recipients
    }
    body = json.dumps(data)

    sqs = boto3.resource('sqs', region_name=current_app.config['SQS_REGION'])
    queue = sqs.get_queue_by_name(
        QueueName=current_app.config['SQS_QUEUE_NAME']
    )
    queue.send_message(
        QueueUrl=current_app.config['SQS_QUEUE_URL'],
        MessageBody=body,
        DelaySeconds=0,
        MessageAttributes={}
    )
