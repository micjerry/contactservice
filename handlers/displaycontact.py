import tornado.web
import tornado.gen
import json
import io
import logging

import motor

class DispayContactHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")

        #begin to logging user
        logging.info("%s begin to display %s" % (userid, contactid))

        result = yield coll.find_one({"id":userid})

        if result:
            userinfo = {}
            contacts = result.get("contacts", [])
            for contact in contacts:
                if (contact["id"] == contactid):
                    userinfo["id"] = contact.get("id", "")
                    userinfo["remark"] = contact.get("remark", "")
                    userinfo["sign"] = "Dance with wolf"
                    userinfo["nickname"] = contact.get("nickname", "")
                    userinfo["sex"] = "man"
                    userinfo["type"] = contact.get("type", "person")
                    break

            if userinfo:
                self.write(userinfo)
            else:
                logging.error("contact %s was not found" % contactid)
                self.set_status(404)
                self.finish()
                return
        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});

        self.finish()
