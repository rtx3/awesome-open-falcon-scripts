#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import socket
import sys
import urllib
import httplib
import time
import base64
import json
from supervisor import childutils
from supervisor.states import ProcessStates
from supervisor.options import make_namespec


KEY = "/cmdb/supervisor"
#AUTH = base64.b64encode('username' + ':' + 'passwords') 

def usage():
    print doc
    sys.exit(255)


class HttpStatus:
    def __init__(self, rpc, programs, any, email, sendmail, optionalheader, etcduser, etcdpassword):
        self.programs = programs
        self.any = any
        self.rpc = rpc
        self.email = email
        self.sendmail = sendmail
        self.optionalheader = optionalheader
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.hostname = self.__hostname()
        self.ip = socket.gethostbyname(self.hostname)
        self.AUTH = base64.b64encode(etcduser + ':' + etcdpassword) 

    def __hostname(self):
        return socket.gethostname()
            
    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                if x['name'] in self.programs and
                (state is None or x['state'] == state)]

    def httpreport(self, key, value):
        headers = {"Content-type": "application/x-www-form-urlencoded", 
                   "Accept": "text/plain", "Authorization": "Basic " + self.AUTH}
        data = urllib.urlencode({'value': value})
        h = httplib.HTTPConnection('localhost:2379')
        url = '/v2/keys' + str(key)
        h.request('PUT', url.strip(), data, headers)
        r = h.getresponse()
        return r.status

    def httponoff(self, key):
        headers = {"Content-type": "application/json", 
                   "Accept": "text/plain", "Authorization": "Basic " + self.AUTH}
        h = httplib.HTTPConnection('localhost:2379')
        url = '/v2/keys' + str(key)
        h.request('GET', url.strip(), headers=headers)
        r = h.getresponse()
        return json.loads(r.read().strip('\n'))['node']['value']

    def write(self, msg):
        self.stderr.write('%s\n' % msg)
        self.stderr.flush()

    def start(self, spec):
        namespec = make_namespec(spec['group'], spec['name'])
        if spec['state'] in (ProcessStates.STOPPED, ProcessStates.EXITED,
                             ProcessStates.FATAL):
            self.write('%s is in STOPPED/EXITED/FATAL state, starting' % namespec)
            try:
                self.rpc.supervisor.startProcess(namespec)
            except Exception as e:
                self.write('Failed to start process %s: %s' % (
                    namespec, e))
        else:
            self.write('%s  in RUNNING state, NOT starting' % namespec)

    def stop(self, spec):
        namespec = make_namespec(spec['group'], spec['name'])
        if spec['state'] in (ProcessStates.RUNNING):
            self.write('%s is in STOPPED state, stopping' % namespec)
            try:
                self.rpc.supervisor.stopProcess(namespec)
            except Exception as e:
                self.write('Failed to stop process %s: %s' % (
                    namespec, e))
        else:
            self.write('%s not in RUNNING state, NOT stopping' % namespec)

    def runforever(self, test=False):
        # 死循环, 处理完 event 不退出继续处理下一个
        while 1:
            # 使用 self.stdin, self.stdout, self.stderr 代替 sys.* 以便单元测试
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            self.stderr.write("HEADERS: {}\n".format(str(headers)))
            self.stderr.write("PAYLOAD: {}\n".format(str(payload)))
            if not headers['eventname'].startswith('TICK'):
                childutils.listener.ok(self.stdout)
                continue
            #specs = self.listProcesses(ProcessStates.RUNNING)
            specs = self.listProcesses()
            self.stderr.write("SPECS: {}\n".format(str(specs)))
            try:
                for proc in specs:
                    if proc['name'] in self.programs:
                        onoff = self.httponoff("{0}/{1}/{2}/ONOFF".format(KEY, self.hostname, proc['name']))
                        if onoff == 'start':
                            self.start(proc)
                        elif onoff == 'stop':
                            self.stop(proc)
                        key = "{0}/{1}/{2}/HTTPOK".format(KEY, self.hostname, proc['name'])
                        value = {}
                        value['httpok'] = int(time.time())
                        value['description'] = proc['description'].split(',')[-1]
                        value['pid'] = proc['pid']
                        value['state'] = proc['statename']
                        d = self.httpreport(key, value)
                        self.stderr.write("REPORT STATUS:{} {} \n".format(proc['name'], str(d)))
                    else:
                        childutils.listener.ok(self.stdout)
                        continue
            except Exception as e:
                self.stderr.write("ERROR: " + str(e))
                childutils.listener.fail(self.stdout)
                continue
     
            self.stderr.flush()
            childutils.listener.ok(self.stdout)
        
    
    def mail(self, email, subject, msg):
        body = 'To: %s\n' % self.email
        body += 'Subject: %s\n' % subject
        body += '\n'
        body += msg
        m = os.popen(self.sendmail, 'w')
        m.write(body)
        m.close()
        self.stderr.write('Mailed:\n\n%s' % body)
        self.mailed = body


def main(argv=sys.argv):
    # 参数解析
    import getopt
    short_args = "u:a:hp:ao:s:m:"
    long_args = [
        "user=",
        "password=",
        "help",
        "program=",
        "any",
        "optionalheader="
        "sendmail_program=",
        "email=",
    ]
    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()
    programs = []
    any = False
    sendmail = '/usr/sbin/sendmail -t -i'
    email = None
    optionalheader = None
    for option, value in opts:
        if option in ('-u', '--user'):
            user = value
        if option in ('-a', '--password'):
            password = value
        if option in ('-h', '--help'):
            usage()
        if option in ('-p', '--program'):
            programs.append(value)
        if option in ('-a', '--any'):
            any = False
        if option in ('-s', '--sendmail_program'):
            sendmail = value
        if option in ('-m', '--email'):
            email = value
        if option in ('-o', '--optionalheader'):
            optionalheader = value
    
    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError as e:
        if e.args[0] != 'SUPERVISOR_SERVER_URL':
            raise
        sys.stderr.write('httpok must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = HttpStatus(rpc, programs, any, email, sendmail, optionalheader, user, password)
    prog.runforever(test=True)
if __name__ == '__main__':
    main()
# Usage
doc = """\
http-ok.py [-p processname] [-a] [-o string] [-m mail_address]
             [-s sendmail] 
Options:
-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'process_name:group_name' syntax.
-a -- Send mail when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmail process invocation.
-o -- Specify a parameter used as a prefix in the mail subject header.
-s -- the sendmail command to use to send email
      (e.g. "/usr/sbin/sendmail -t -i").  Must be a command which accepts
      header and message data on stdin and sends mail.  Default is
      "/usr/sbin/sendmail -t -i".
-m -- specify an email address.  The script will send mail to this
      address when crashmail detects a process crash.  If no email
      address is specified, email will not be sent.
The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.
A sample invocation:
http-ok.py -p program1 -p group1:program2 -m dev@example.com
"""