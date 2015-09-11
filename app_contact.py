import os
import sys

sys.path.append('/opt/webapps/libs')

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.options
import logging
import logging.handlers

import motor
from mickey.daemon import Daemon
import mickey.logutil

from handlers.listcontact import ListContactHandler
from handlers.addcontact import AddContactHandler
from handlers.displaycontact import DispayContactHandler
from handlers.rmvcontact import RmvContactHandler
from handlers.markcontact import MarkContactHandler

import mickey.publish

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers=[(r"/contact/list/contacts", ListContactHandler),
                  (r"/contact/add/friend", AddContactHandler),
                  (r"/contact/display/detail", DispayContactHandler),
                  (r"/contact/remove/friend", RmvContactHandler),
                  (r"/contact/mod/remark", MarkContactHandler)
                 ]
        self.db = motor.MotorClient("mongodb://localhost:27017").contact
        self.publish = mickey.publish
        tornado.web.Application.__init__(self, handlers, debug=True)
 
class MickeyDamon(Daemon):
    def run(self):
        tornado.options.parse_command_line()
        mickey.logutil.setuplog()
        http_server = tornado.httpserver.HTTPServer(Application())
        http_server.listen(options.port)
        tornado.ioloop.IOLoop.instance().start()

    def errorcmd(self):
        print("unkown command")


def micmain():
    if len(sys.argv) < 2:
        print("invalid command")
        return

    pid_file_name = "/var/run/" + sys.argv[0].replace(".py", ".pid")
    miceydamon = MickeyDamon(pid_file_name)
    handler = {}
    handler["start"] = miceydamon.start
    handler["stop"] = miceydamon.stop
    handler["restart"] = miceydamon.restart
    handler["run"] = miceydamon.run

    return handler.get(sys.argv[1],miceydamon.errorcmd)()

if __name__ == "__main__":
    micmain()    
