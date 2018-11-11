#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ********************************************************************************
# Copyright © 2018 jianglin
# File Name: encrypt.py
# Author: jianglin
# Email: mail@honmaple.com
# Created: 2018-03-17 17:52:05 (CST)
# Last Update: Tuesday 2018-11-06 13:52:22 (CST)
#          By:
# Description:
# ********************************************************************************
from flask import request, current_app
from flask.views import MethodView
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from maple.extension import csrf
from maple.response import HTTP


class Encrypt(object):
    def __init__(self, password, salt):
        if isinstance(salt, str):
            salt = salt.encode("utf-8")
        self.fernet = Fernet(self.password(password, salt))

    def password(self, raw_password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend())
        return urlsafe_b64encode(kdf.derive(raw_password.encode("utf-8")))

    def encrypt(self, text):
        return self.fernet.encrypt(text.encode("utf-8")).decode("utf-8")

    def decrypt(self, text):
        return self.fernet.decrypt(text.encode("utf-8")).decode("utf-8")


class EncryptAPI(MethodView):
    decorators = (csrf.exempt, )

    def post(self):
        request_data = request.data
        password = request_data.pop('password', '')
        content = request_data.pop('content', '')
        if not password or not content:
            return HTTP.BAD_REQUEST(message="params required.")
        ec = Encrypt(password, current_app.config['SECRET_KEY_SALT'])
        try:
            return HTTP.OK(data=ec.decrypt(content))
        except InvalidToken:
            return HTTP.BAD_REQUEST(message="password is not correct")
