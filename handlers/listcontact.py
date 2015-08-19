import tornado.web
import tornado.gen
import json
import io
import logging

import motor

import basehandler

class ListContactHandler(basehandler.BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")

        logging.info("list contact for %s" % userid)

        if self.p_userid != userid:
            logging.error("you can not query other user info")
            self.set_status(403)
            self.finish()
            return

        user = yield coll.find_one({"id":userid})
        if user:
            contacts = user.get("contacts", [])
            appends = user.get("appendings", [])

            rs_contacts = []
            for item in contacts:
                contact = {}
                c_id = item.get("id", "")
                contact["id"] = c_id
                contact["remark"] = item.get("remark", "")
                contact["type"] = item.get("type", "")
                contact_db = yield coll.find_one({"id":c_id})
                if contact_db:
                    contact["nickname"] = contact_db.get("nickname", "")
                    contact["sign"] = contact_db.get("sign", "")

                rs_contacts.append(contact)

            self.write({"contacts": rs_contacts,"appendings":appends});

        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()
