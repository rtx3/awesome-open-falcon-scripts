#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import socket
import sys
import urllib
import httplib
import time
from supervisor import childutils
from supervisor.states import ProcessStates

KEY = "/cmdb/supervisor"


def usage():
    print doc
    sys.exit(255)


class HttpStatus:
    def __init__(self, rpc, programs, any, email, sendmail, optionalheader):
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

    def __hostname(self):
        return socket.gethostname()
            
    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                if x['name'] in self.programs and
                (state is None or x['state'] == state)]

    def httpreport(self, key, value):
        headers = {"Content-type": "application/x-www-form-urlencoded", 
                   "Accept": "text/plain"}
        data = urllib.urlencode({'value': value})
        h = httplib.HTTPConnection('localhost:2379')
        url = '/v2/keys' + str(key)
        h.request('PUT', url.strip(), data, headers)
        r = h.getresponse()
        return r.status

    def runforever(self, test=False):
        # 死循环, 处理完 event 不退出继续处理下一个
        while 1:
            # 使用 self.stdin, self.stdout, self.stderr 代替 sys.* 以便单元测试
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            self.stderr.write("HEADERS: {}\n".format(str(headers)))
            self.stderr.write("PAYLOAD: {}\n".format(str(payload)))
            if not headers['eventname'].startswith('PROCESS_STATE'):
                childutils.listener.ok(self.stdout)
                continue
            
            self.stderr.write("EVENT: {}\n".format(headers['eventname']))
            try:
                pheaders, pdata = childutils.eventdata(payload + '\n') 
                if pheaders['processname'] in self.programs:
                    key = "{0}/{1}/{2}/HTTPSTATUS".format(KEY, self.hostname, pheaders['processname'])
                    value = headers['eventname'].split('_')[-1]
                    d = self.httpreport(key, value)
                    self.stderr.write("REPORT STATUS:{} {} \n".format(pheaders['processname'], str(d)))
                else:
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
    short_args = "hp:ao:s:m:"
    long_args = [
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

    prog = HttpStatus(rpc, programs, any, email, sendmail, optionalheader)
    prog.runforever(test=True)
if __name__ == '__main__':
    main()
# Usage
doc = """\
http-status.py [-p processname] [-a] [-o string] [-m mail_address]
             [-s sendmail] URL
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
http-status.py -p program1 -p group1:program2 -m dev@example.com
"""