#!/usr/bin/env python
# -*-coding:utf8-*-
__author__ = 'Kairong'
from app import config
from app import app
app.run(debug=True, host='127.0.0.1', port=config.Srv_port)