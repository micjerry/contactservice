import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.options
import logging
import logging.handlers

import motor

from handlers.listcontact import ListContactHandler
from handlers.addcontact import AddContactHandler
from handlers.displaycontact import DispayContactHandler
from handlers.rmvcontact import RmvContactHandler
from handlers.markcontact import MarkContactHandler

import publish

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
        self.publish = publish
        tornado.web.Application.__init__(self, handlers, debug=True)
 
def setuplog():
    ROOT = os.path.dirname(os.path.abspath(__file__))
    path = lambda *a:os.path.join(ROOT, *a)

    #setup access log
    access_log = logging.getLogger("tornado.access")
    access_log.setLevel(logging.DEBUG)
    accessHandler = logging.handlers.RotatingFileHandler(
      path('log/access.log'), maxBytes=50000000, backupCount=5)
    access_log.addHandler(accessHandler)

    #setup app log
    app_log = logging.getLogger("tornado.application")
    app_log.setLevel(logging.DEBUG)
    appHandler = logging.handlers.RotatingFileHandler(
      path('log/app.log'),  maxBytes=50000000, backupCount=5)
    app_log.addHandler(appHandler)

    #setup gen log
    gen_log = logging.getLogger("tornado.general")
    gen_log.setLevel(logging.DEBUG)
    genHandler = logging.handlers.RotatingFileHandler(
      path('log/gen.log'),  maxBytes=50000000, backupCount=5)
    gen_log.addHandler(genHandler)

    #setup service log
    service_log = logging.getLogger('')
    service_log.setLevel(logging.DEBUG)
    serviceHandler = logging.handlers.RotatingFileHandler(
      path('log/service.log'),  maxBytes=50000000, backupCount=5)
    formatter = logging.Formatter('%(pathname)s %(filename)s %(funcName)s %(lineno)d %(asctime)s %(levelname)s %(message)s')
    serviceHandler.setFormatter(formatter)
    service_log.addHandler(serviceHandler)
 
if __name__ == "__main__":
    tornado.options.parse_command_line()
    setuplog()
    
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
