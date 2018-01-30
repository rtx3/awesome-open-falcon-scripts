#!/usr/bin/env python
# -*-coding:utf8-*-
# rtx3 <r@rtx3.com>


from os import popen as ctl
import pub


DB_host = "127.0.0.1"
DB_port = 3306
DB_user = "root"
DB_passwd = ""

if DB_passwd:
    CMD = "mysql -u%s -p%s -h%s -P%d " % (DB_user, DB_passwd, DB_host, DB_port)
else:
    CMD = "mysql -u%s -h%s -P%d " % (DB_user, DB_host, DB_port)

METRICS = ['Questions',
           'Com_commit',
           'Com_rollback',
           'Uptime']


def get_mysql_status():
    ret = {}
    for item in METRICS:
        result = ctl(CMD + ' -e \"show  global  status like \'' 
                           + str(item) + '%\'\"').readlines()
        status = result[1].split("\t")[1].strip('\n')
        try:
            assert(isinstance(int(status), (int, long)))
            ret[item] = int(status)
        except AssertionError:
            continue
    return ret


def main():
    ret = get_mysql_status()
    print ret
    #push_date = pub.P_data()
    #push_date.add(metric="Question", value=ret['Questions'], tag="srv=mysql")
    #push_date.add(metric="QPS", value=int(ret['Questions']), tag="srv=mysql", counterType="COUNTER")
    #push_date.add(metric="Transaction", value=int(ret['Questions']) + , tag="srv=mysql")
    #push_date.add(metric="TPS", value=tps_counter, tag="srv=mysql", counterType="COUNTER")
    #push_date.push()


if __name__ == "__main__":
    main()