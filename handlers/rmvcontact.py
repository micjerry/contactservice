import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

from mickey.basehandler import BaseHandler

class RmvContactHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish

        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")
        flag = str(uuid.uuid4()).replace('-', '_')

        logging.info("%s begin to remove %s" % (userid, contactid))

        if self.p_userid != userid:
            logging.error("forbiden you can not change other user")
            self.set_status(403)
            self.finish()
            return

        result = yield coll.find_and_modify({"id":userid}, 
                                            {
                                              "$pull":{"contacts":{"id":contactid}, "appendings":{"id":contactid}},
                                              "$set": {"flag" : flag}
                                            })


        #update contact
        c_result = yield coll.find_and_modify({"id":contactid},
                                            {
                                              "$pull":{"contacts":{"id": userid}},
                                              "$set": {"flag" : flag}
                                            })

        #handle contact
        if c_result:
            if userid in [x.get("id", "") for x in c_result.get("contacts", [])]:
                #set break relation flag
                break_rst = yield coll.find_and_modify({"id":contactid},
                                            {
                                              "$push":{"appendings":{"id": userid,"action":"break"}},
                                              "$set": {"flag" : flag}
                                            })
                #notify the contact
                notify = {
                 "name": "mx.contact.rmv_contact",
                 "userid": userid,
                 "pub_type": "any",
                 "nty_type": "app"
                }
                publish.publish_one(contactid, notify)

                #notify user self
                self_notify = {
                 "name": "mx.contact.self_rmv_contact",
                 "userid": contactid,
                 "pub_type": "online",
                 "nty_type": "app"
                }

                publish.publish_one(userid, self_notify)

        if result:
            if contactid in [x.get("id", "") for x in result.get("appendings", [])]:
                if not contactid in [x.get("id", "") for x in result.get("contacts", [])]:
                    #notify the user
                    notify = {
                     "name": "mx.contact.self_rmv_appendings",
                     "userid": contactid,
                     "pub_type": "online",
                     "nty_type": "app"
                    }

                    publish.publish_one(userid, notify)

            self.set_status(200)
            
        else:
            logging.info("remove failed")
            self.set_status(404)
            self.write({"error":"not found"});

        self.finish()
