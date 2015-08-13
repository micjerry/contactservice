import tornado.web
import tornado.gen
import json
import io
import logging

import motor

class ListContactHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")

        logging.info("list contact for %s" % userid)

        user = yield coll.find_one({"id":userid})
        if user:
            contacts = user.get("contacts", [])
            appends = user.get("appendings", [])

            self.write({"contacts": contacts,"appendings":appends});
        else:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.write({"error":"not found"});
        self.finish()
