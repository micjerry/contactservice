import tornado.web
import tornado.gen
import json
import io
import logging

import motor

class RmvContactHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")

        logging.info("%s begin to remove %s" % (userid, contactid))

        result = yield coll.find_and_modify(
                           {"id":userid}, 
                           {"$pull":{"contacts":{"id":contactid}}}
                       )
        append_result = yield coll.find_and_modify(
                           {"id":userid},
                           {"$pull":{"appendings":{"id":contactid}}}
                       )
        if result:
            self.set_status(200)
        else:
            logging.info("mark failed")
            self.set_status(404)
            self.write({"error":"not found"});

        self.finish()
