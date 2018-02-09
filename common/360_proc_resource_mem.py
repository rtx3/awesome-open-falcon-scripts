#!/usr/bin/env python
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

class Resource():
    def __init__(self, pid, tag):
        self.host = socket.gethostname()
        self.pid = pid
        self.tag = tag

    def get_cpu_user(self):
        cmd="cat /proc/" + str(self.pid)  +  "/stat |awk '{print $14+$16}'"
        return os.popen(cmd).read().strip("\n")

    def get_cpu_sys(self):
        cmd="cat /proc/" + str(self.pid)  +  "/stat |awk '{print $15+$17}'"
        return os.popen(cmd).read().strip("\n")

    def get_cpu_all(self):
        cmd="cat /proc/" + str(self.pid)  +  "/stat |awk '{print $14+$15+$16+$17}'"
        return os.popen(cmd).read().strip("\n")

    def get_mem(self):
        cmd="cat /proc/" + str(self.pid)  +  "/status |grep VmRSS |awk '{print $2*1024}'"
        return os.popen(cmd).read().strip("\n")

    def get_swap(self):
        cmd="cat /proc/" + str(self.pid)  +  "/stat |awk '{print $(NF-7)+$(NF-8)}' "
        return os.popen(cmd).read().strip("\n")

    def get_fd(self):
        cmd="cat /proc/" + str(self.pid)  +  "/status |grep FDSize |awk '{print $2}'"
        return os.popen(cmd).read().strip("\n")

    def run(self):
        self.resources_d={
            'process.cpu.user':[self.get_cpu_user,'COUNTER'],
            'process.cpu.sys':[self.get_cpu_sys,'COUNTER'],
            'process.cpu.all':[self.get_cpu_all,'COUNTER'],
            'process.mem':[self.get_mem,'GAUGE'],
            'process.swap':[self.get_swap,'GAUGE'],
            'process.fd':[self.get_fd,'GAUGE']
        }

        if not os.path.isdir("/proc/" + str(self.pid)):
            return

        output = []
        for resource in self.resources_d.keys():
                t = {}
                t['endpoint'] = self.host
                t['timestamp'] = int(time.time())
                t['step'] = 360
                t['counterType'] = self.resources_d[resource][1]
                t['metric'] = resource
                t['value'] = self.resources_d[resource][0]()
                t['tags'] = "pid=%s,pro_cmd=%s" % (self.pid, self.tag)

                output.append(t)

        return output

    def dump_data(self):
        return json.dumps()


def push(data):
    senddata = json.dumps(data)
    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    h = httplib.HTTPConnection(PUSH_PATH)        
    h.request('POST', '/v1/push', senddata, headers)
    print json.dumps(data)      
    return 0


def get_pid():
    cmd = "ps aux | awk '{print $2, $4, $11}' | sort -k2rn | head -n 5"
    ret = []
    for item in os.popen(cmd).readlines():
        pid = {}
        try:
            assert(isinstance(int(item.split()[0]), (int, long)))
        except AssertionError:
            print "ERROR: key is not int."
            continue
        pid[int(item.split()[0])] = item.split()[-1].strip("\n")
        ret.append(pid)
    return ret

if __name__ == "__main__":
    pids = get_pid()
    #print pids
    payload = []
    for item in pids:
        for pid in item:            
            d = Resource(pid=pid, tag=item[pid]).run()
            if d:
                payload.extend(d)
    try:    
        push(payload)    
    except Exception:    
        print "ERROR " + json.dumps(payload)


