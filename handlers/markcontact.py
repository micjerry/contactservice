import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid
from mickey.basehandler import BaseHandler

class MarkContactHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")
        remark = data.get("remark", "")
        flag = str(uuid.uuid4()).replace('-', '_')

        logging.info("user %s begin to mark contact %s as %s" % (userid, contactid, remark))
        
        if self.p_userid != userid:
            logging.error("forbiden you can not change other user")
            self.set_status(403)
            self.finish()
            return

        result = yield coll.find_one({"id":userid})
        if result:
            contacts = result.get("contacts", [])
            for contact in contacts:
                if (contact.get("id", "") == contactid):
                    contact["remark"] = remark
                    break

            modresult = yield coll.find_and_modify(
                           {"id":userid},
                           {"$set":
                              {
                               "contacts" : contacts,
                               "flag" : flag
                              }
                           }
                       )
            if modresult:
                self.set_status(200)
            else:
                logging.info("mark failed")
                self.set_status(500)
        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()
