import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

import mickey.userfetcher
from mickey.basehandler import BaseHandler

import libcontact

class UnBindDeviceHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish
        token = self.request.headers.get("Authorization", "")

        #get parameters of request
        data         = json.loads(self.request.body.decode("utf-8"))
        deviceid     = data.get("deviceid", "")
        contacts     = data.get("contacts", [])

        logging.info("begin to cancel bind request, user = %s, device = %s" % (self.p_userid, deviceid))
        
        if not deviceid:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        self_unbind = False
        if len(contacts) == 1 and contacts[0] == self.p_userid:
            self_unbind = True

        if not self_unbind:
            isadmin = yield libcontact.check_admin(self.p_userid, deviceid)
            if not isadmin:
                logging.error("you are not the admin")
                self.set_status(403)
                self.finish()
                return

        username = ""
        devicename = ""
        res_device = yield mickey.userfetcher.getcontact(deviceid, token)

        if res_device:
            devicename = res_device.get("commName", "")

        binders = yield libcontact.get_binders(deviceid)

        for item in contacts:
            phone = yield libcontact.get_bindphone(item)
            if not phone:
                continue

            yield libcontact.un_bind(deviceid, phone)
            res_user = yield mickey.userfetcher.getcontact(item, token)
            if res_user:
                username = res_user.get("commName", "")

            notify = {
                "name": "mx.contact.quitbinder",
                "deviceid": deviceid,
                "devicename": devicename,
                "userid": item,
                "username": username,
                "removeby":self.p_userid,
                "pub_type": "any",
                "nty_type": "app",
                "msg_type": "other",
                }

            publish.publish_multi(binders, notify)



        self.set_status(200)
        self.finish()



