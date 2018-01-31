#!/bin/env python
#-*- coding:utf-8 -*-

import os
import os.path
import socket
import time
import json

import httplib


PUSH_PATH = "127.0.0.1:1988"
API_PATH = "localhost:8088"
PREFIX = "hadoop."
TAGS = ""
API = "/ws/v1/cluster/metrics"
STEP = 360


class Resource():
    def __init__(self, metrics, tag=None):
        self.host = socket.gethostname()
        self.metrics = metrics
        self.resources_d = {}
        self.tag = TAGS

    def run(self):
        for metric in self.metrics:
            resource_list = []
            for key in metric.keys():
                resource_list.append(metric[key])
                resource_list.append('GAUGE')
                self.resources_d[PREFIX + key] = resource_list
        output = []
        for resource in self.resources_d.keys():
                t = {}
                t['endpoint'] = self.host
                t['timestamp'] = int(time.time())
                t['step'] = STEP
                t['counterType'] = self.resources_d[resource][1]
                t['metric'] = resource
                t['value'] = self.resources_d[resource][0]
                t['tags'] = "%s" % (self.tag)

                output.append(t)

        return output


def push(data):
    data = json.dumps(data)
    headers = {"Content-type": "application/json", "Accept": "text/plain"}   
    try:
        h = httplib.HTTPConnection(PUSH_PATH)        
        h.request('POST', '/v1/push', data, headers)
    except Exception:
        print "Pushing Failed when sending data."
        return 1
    print "Pushing finished."        
    return 0


def get_resources():
    cmd = "curl -s http://" + API_PATH + API
    result = os.popen(cmd).readlines()
    ret = json.loads(result[0])['clusterMetrics']
    return ret

if __name__ == "__main__":
    resources = get_resources()
    print resources
    print "Pushing...."
    d = Resource(metrics=resources).run()
    print d
    #if d:
    #    push(d)
    #else:
    #    print "Pushing Failed."
            #if d:
            #    print "OK. " + str(idx)
            #else:
    #for idx, item in enumerate(resources):
    #    for resource in item:            
    #        print "Pushing" + str(resource) 
            #d = Resource(metric=resource, tag=item[resource]).run()
            #if d:
            #    print "OK. " + str(idx)
            #else:
            #    print "Fail." + str(idx)

