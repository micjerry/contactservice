import tornado.web
import tornado.gen
import json
import io
import logging

import motor

import mickey.userfetcher
from mickey.basehandler import BaseHandler

class TransferDeviceHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        devices = data.get("devices", [])
        userid = data.get("userid", "")

        logging.info("%s transfer device %r to %s" % (self.p_userid, devices, userid))
        if not devices or not userid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        user = yield coll.find_one({"id":self.p_userid})
        if not user:
            logging.error("user %s was not found" % self.p_userid)
            self.set_status(404)
            self.finish()
            return
        
        #remove device from transfer
        result = yield coll.find_and_modify({"id":self.p_userid},
                                            {
                                              "$pullAll":{"devices": devices}
                                            })
        if not result:
            logging.error("transfer failed remove failure")
            self.set_status(500)
            self.finish()
            return

        #add device to transfee
        result = yield coll.find_and_modify({"id":userid},
                                            {
                                              "$push":{"devices": {"$each": devices}},
                                              "$unset": {"garbage": 1}
                                            })

        if not result:
            logging.error("transfer failed add failure")
            self.set_status(500)
            self.finish()
            return

        self.set_status(200)
        self.finish()
