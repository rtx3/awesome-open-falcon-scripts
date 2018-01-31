#!/usr/bin/python
# -*- coding: utf-8 -*-
# A event listener meant to be subscribed to PROCESS_STATE_CHANGE
# events.  It will send mail when processes that are children of
# supervisord transition unexpectedly to the EXITED state.
import os
import socket
import sys
from supervisor import childutils
from supervisor.states import ProcessStates

def usage():
    print doc
    sys.exit(255)
class HttpStatus:
    def __init__(self, programs, any, email, sendmail, optionalheader):
        self.programs = programs
        self.any = any
        self.email = email
        self.sendmail = sendmail
        self.optionalheader = optionalheader
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
    def listProcesses(self, state=None):
        return [x for x in self.rpc.supervisor.getAllProcessInfo()
                   if x['name'] in self.programs and
                      (state is None or x['state'] == state)]
    def runforever(self, test=False):
        # 死循环, 处理完 event 不退出继续处理下一个
        while 1:
            # 使用 self.stdin, self.stdout, self.stderr 代替 sys.* 以便单元测试
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            if test:
                self.stderr.write(str(headers) + '\n')
                self.stderr.write(payload + '\n')
                self.stderr.flush()
            if not headers['eventname'].startswith('TICK'):
                childutils.listener.ok(self.stdout)
                continue
            specs = self.listProcesses(ProcessStates.RUNNING)
            self.stdin.write("RUNING:"+str(specs))
            # 解析 payload, 这里我们只用这个 pheaders.
            # pdata 在 PROCESS_LOG_STDERR 和 PROCESS_COMMUNICATION_STDOUT 等类型的 event 中才有
            #pheaders, pdata = childutils.eventdata(payload + '\n')
            # 过滤掉 expected 的 event, 仅处理 unexpected 的
            # 当 program 的退出码为对应配置中的 exitcodes 值时, expected=1; 否则为0
            #if int(pheaders['expected']):
            #    childutils.listener.ok(self.stdout)
            #    continue
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            # 构造报警内容
            #msg = "Host: %s(%s)\nProcess: %s\nPID: %s\nEXITED unexpectedly from state: %s" % \
            #      (hostname, ip, pheaders['processname'], pheaders['pid'], pheaders['from_state'])
            #subject = ' %s crashed at %s' % (pheaders['processname'],
            #                                 childutils.get_asctime())
            #if self.optionalheader:
            #    subject = '[' + self.optionalheader + ']' + subject
            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()
            #self.mail(self.email, subject, msg)
            # 向 stdout 写入"RESULT\nOK"，并进入下一次循环
            childutils.listener.ok(self.stdout)
    # 发送邮件, 可以用自己的, 也可以抽出来作为一个 module 复用
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
    # listener 必须交由 supervisor 管理, 自己运行是不行的
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashmail must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return
    prog = HttpStatus(programs, any, email, sendmail, optionalheader)
    prog.runforever(test=True)
if __name__ == '__main__':
    main()
# Usage
doc = """\
crashmail.py [-p processname] [-a] [-o string] [-m mail_address]
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
crashmail.py -p program1 -p group1:program2 -m dev@example.com
"""