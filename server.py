import os
import sys

command = ""
dirname = ""
appname = "app_contact.py"
appname_print = ""

def prepare():
    if (len(sys.argv) < 2):
        print("invalid command")
        sys.exit()

    global command
    global dirname
    global appname
    global appname_print 

    command = sys.argv[1]
    dirname = os.path.dirname(sys.argv[0])
    appname_print = appname.replace(".py", "")

    # create log dir
    log_path = dirname + "log"
    if not os.path.exists(log_path):
        os.makedirs(log_path)

def start():
    ps_id = os.popen("ps -ef | grep %s | grep -v grep | awk '{print $2}'" % appname).read()
    if ps_id:
        print("%s was already started, pid = %s" % (appname_print, ps_id))
        return
    else:
        os.popen("python %s & >/dev/null 2>&1" % appname)
        print("%s started" % appname_print)

def stop():
    ps_id = os.popen("ps -ef | grep %s | grep -v grep | awk '{print $2}'" % appname).read()
    if ps_id:
        os.popen("kill -9 " + ps_id)
        print("%s stopped" % appname_print)


def restart():
    stop()
    start()


if __name__ == "__main__":
    prepare()

    if command == "start":
        start()
    elif command == "stop":
        stop()
    elif command == "restart":
        restart()
    else:
        print("invalid command")
