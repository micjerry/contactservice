import tornado.web
import tornado.gen
import json
import io
import logging

from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

class TransferDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        publish = self.application.publish
        data = json.loads(self.request.body.decode("utf-8"))
        devices = data.get("devices", [])
        userid = data.get("userid", "")

        logging.info("%s transfer device %r to %s" % (self.p_userid, devices, userid))
        if not devices or not userid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        ever_failed = False

        for item in devices:
            transfer_rst = yield mickey.userfetcher.transferbind(self.p_userid, item, 'ADMIN', userid)
            if transfer_rst != 200:
                logging.error("transfer device %s to %s by %s failed" % (item, userid, self.p_userid))
                ever_failed = True
                continue
        
        if ever_failed == True:
            logging.error("transfer failed remove failure")
            self.set_status(500)
            self.finish()
            return

        notify = {
              "name": "mx.contact.device_transfer",
              "pub_type": "any",
              "nty_type": "app",
              "msg_type": "other",
              "userid": self.p_userid,
              "devices" : devices
            }

        publish.publish_one(userid, notify)

        self.set_status(200)
        self.finish()
