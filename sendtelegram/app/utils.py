#!/usr/bin/env python
# -*-coding:utf8-*-
from app import config
import urllib
import urllib2


def sendmsg(text):
    try:
        params = urllib.urlencode({'chat_id': config.CHAT_ID, 'text': text})
        urllib2.urlopen(config.TELE_API + '?' + params)
        return True
    except Exception as e:
        print str(e)
        return False