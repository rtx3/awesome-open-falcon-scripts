#!/bin/env python
#-*- encoding:utf-8 -*-
from time import time
import json
import urllib, httplib

PUSH_PATH = "127.0.0.1:1988"


class P_data(object):
    def __init__(self):
        self.result = []
        self.Endpoint = get_endpoint()
        self.ts = int(time())

    def add(self, metric, value, tag, counterType="GAUGE", step=60):
        self.result.append({
            "endpoint": self.Endpoint,
            "metric": metric,
            "timestamp": self.ts,
            "step": step,
            "value": value,
            "counterType": counterType,
            "tags": tag,
        })

    def get(self):
        return self.result

    def out(self):
        return json.dumps(self.result)

    def push(self):
        data = json.dumps(self.result)
        h = httplib.HTTPConnection(PUSH_PATH)        
        h.request('POST', '/v1/push', data)        
        r = h.getresponse()        
        print r.read()


def get_endpoint():
    from socket import gethostname
    return gethostname()