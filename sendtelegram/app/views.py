#!/usr/bin/env python
# -*-coding:utf8-*-
from flask import request
from app import app
import utils


@app.route("/")
def sendmail_index():
    """默认首页"""
    return "hello sendmail"


@app.route("/chk")
def chk_health():
    """存活检测"""
    return "ok"


@app.route("/tele_msg", methods=["POST"])
def msg():
    msg_content = request.form["content"]
    print msg_content
    if utils.sendmsg(msg_content):
        return "ok"
    else:
        return "false"
