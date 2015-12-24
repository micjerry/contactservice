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
import mickey.commonconf
import mickey.logutil

from handlers.listcontact import ListContactHandler
from handlers.addcontact import AddContactHandler
from handlers.displaycontact import DispayContactHandler
from handlers.rmvcontact import RmvContactHandler
from handlers.markcontact import MarkContactHandler
from handlers.starcontact import StarContactHandler
from handlers.fetchdevice import FetchDeviceHandler
from handlers.listdevices import ListDeviceHandler
from handlers.transferdevice import TransferDeviceHandler
from handlers.displaycomb import DisplayCombHandler
from handlers.fetchorder import FetchOrderHandler
from handlers.bindcontacttodevice import BindContactToDeviceHandler
from handlers.acceptbind import AcceptBindHandler
from handlers.scanbindtodevice import ScanBindToDeviceHandler
from handlers.unbinddevice import UnBindDeviceHandler
from handlers.displayuser import DispayUserHandler
from handlers.moduser import ModUserHandler

import mickey.publish

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)
define("cmd", default="run", help="Command")
define("conf", default="/etc/mx_apps/app_contact/app_contact_is1.conf", help="Server config")
define("pidfile", default="/var/run/app_contact_is1.pid", help="Pid file")
define("logfile", default="/var/log/app_contact_is1", help="Log file")

class Application(tornado.web.Application):
    def __init__(self):
        handlers=[(r"/contact/list/contacts", ListContactHandler),
                  (r"/contact/add/friend", AddContactHandler),
                  (r"/contact/display/detail", DispayContactHandler),
                  (r"/contact/remove/friend", RmvContactHandler),
                  (r"/contact/mod/remark", MarkContactHandler),
                  (r"/contact/mod/star", StarContactHandler),
                  (r"/contact/fetch/devices", FetchDeviceHandler),
                  (r"/contact/list/devices", ListDeviceHandler),
                  (r"/contact/transfer/device", TransferDeviceHandler),
                  (r"/contact/display/comb", DisplayCombHandler),
                  (r"/contact/fetch/order", FetchOrderHandler),
                  (r"/contact/device/addbinders", BindContactToDeviceHandler),
                  (r"/contact/device/acceptbind", AcceptBindHandler),
                  (r"/contact/device/scanbind", ScanBindToDeviceHandler),
                  (r"/contact/device/unbind", UnBindDeviceHandler),
                  (r"/contact/user/display", DispayUserHandler),
                  (r"/contact/user/mod", ModUserHandler)
                 ]
        self.db = motor.MotorClient(options.mongo_url).contact
        self.publish = mickey.publish
        tornado.web.Application.__init__(self, handlers, debug=True)
 
class MickeyDamon(Daemon):
    def run(self):
        mickey.logutil.setuplog(options.logfile)
        http_server = tornado.httpserver.HTTPServer(Application())
        http_server.listen(options.port, options.local_server)
        tornado.ioloop.IOLoop.instance().start()

    def errorcmd(self):
        print("unkown command")


def micmain():
    tornado.options.parse_command_line()
    tornado.options.parse_config_file(options.conf)

    miceydamon = MickeyDamon(options.pidfile)
    handler = {}
    handler["start"] = miceydamon.start
    handler["stop"] = miceydamon.stop
    handler["restart"] = miceydamon.restart
    handler["run"] = miceydamon.run

    return handler.get(options.cmd, miceydamon.errorcmd)()

if __name__ == "__main__":
    micmain()    
