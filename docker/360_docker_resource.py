#!/bin/env python
#-*- coding:utf-8 -*-

import os,sys
import os.path
from os.path import isfile
from traceback import format_exc
import xmlrpclib
import socket
import time
import json
import copy
import httplib


PUSH_PATH = "127.0.0.1:1988"
PREFIX = "docker."
TAGS = ""
STEP = 360


class Resource():
    def __init__(self, metrics, tag=None):
        self.host = socket.gethostname()
        self.metrics = metrics
        self.resources_d = {}
        self.tag = TAGS

    def run(self):
        for metric in self.metrics:
            resource_list_cpu = []
            resource_list_mem = []
            for key in metric:
                resource_list_cpu.append(metric[key][0])
                resource_list_cpu.append('GAUGE')
                self.resources_d[PREFIX + key + '.CPU'] = resource_list_cpu
                resource_list_mem.append(metric[key][1])
                resource_list_mem.append('GAUGE')
                self.resources_d[PREFIX + key + '.MEM'] = resource_list_mem
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

    def dump_data(self):
        return json.dumps()


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
    cmd = "docker stats --no-stream|\
           awk 'NR>1{print $2, $3, $7}'"
    ret = []
    for item in os.popen(cmd).readlines():
        print item
        resource = {}
        resource[item.split()[0]] = [item.split()[1].strip("\n").strip("%"),
                                     item.split()[2].strip("\n").strip("%")]
        ret.append(resource)
    return ret


def check_docker_version():
    cmd = "docker -v|awk '{print $3}'"
    result = os.popen(cmd).readlines()
    print result
    docker_version = result.split('.')
    print docker_version


if __name__ == "__main__":
    check_docker_version()
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

