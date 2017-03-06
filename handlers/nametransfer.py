import tornado.web
import tornado.gen
import json
import io
import logging

import mickey.userfetcher
from mickey.basehandler import BaseHandler

class NameTransferHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        if not self._decoded_reqbody:
            self._decoded_reqbody = json.loads(self.request.body.decode("utf-8"))

        users = self._decoded_reqbody.get("users", [])

        logging.info("transfer name")

        if not users:
            logging.error("users is null")
            self.set_status(403)
            self.finish()
            return

        rs_contacts = []
        for item in users:
            contact = {}
            contact["id"] = item
            c_userinfo = yield mickey.userfetcher.getcontact(item)
            if c_userinfo:
                contact["nickname"] = c_userinfo.get("commName", "")

            rs_contacts.append(contact)

        self.write({"users": rs_contacts})

        self.finish()

