import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import uuid

from mickey.basehandler import BaseHandler
import tornado_mysql
from mickey.mysqlcon import get_mysqlcon

_checkdevice_sql = """
  SELECT device_userID FROM deviceusermap WHERE device_userID = %s AND userEntity_userID = %s;
"""

class AddContactHandler(BaseHandler):
    USERTYPE_PERSON    = "PERSON"
    USERTYPE_TERMINAL  = "TERMINAL"
    ADDTYPE_OK         = "ok"
    ADDTYPE_AUTH       = "auth required"

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish

        #get parameters of request
        data         = json.loads(self.request.body.decode("utf-8"))
        userid       = data.get("id", "invalid")
        contactid    = data.get("contactid", "invalid")
        usertype     = data.get("usertype", self.USERTYPE_PERSON).upper()
        contact_type = data.get("type", self.USERTYPE_PERSON).upper()
        user_nick    = data.get("nickname", "")
        contact_nick = data.get("contactnick", "")
        comment      = data.get("comment", "")
        addtype      = data.get("addtype", "").lower()
        change_flag  = str(uuid.uuid4()).replace('-', '_')

        logging.info("begin to handle add contact request, userid = %s contact = %s type = %s nick = %s cnick = %s" % (userid, contactid, contact_type, user_nick, contact_nick))

        if self.p_userid != userid:
            logging.error("forbiden you can not change other user")
            self.set_status(403)
            self.finish()
            return

        if contactid == userid:
            logging.error("add your self?")
            self.set_status(403)
            self.finish()
            return

        if contact_type != self.USERTYPE_TERMINAL and contact_type != self.USERTYPE_PERSON:
            logging.error("invalid contact type")
            self.set_status(403)
            self.finish()
            return

        #check parameters        
        user = yield coll.find_one({"id":userid})
        contact = yield coll.find_one({"id":contactid})
        if user:

            # notify send to contact
            notify = {
              "name": "mx.contact.add_contact",
              "userid": userid,
              "comment": comment,
              "nickname": user_nick,
              "usertype": usertype,
              "pub_type": "any",
              "nty_type": "app",
              "msg_type": "other",
              "addtype": addtype
            }

            # response body
            body = {}

            # check is repeat add
            contacts = user.get("contacts", [])
            appendings = user.get("appendings", [])

            if contactid in [x.get("id", "") for x in user.get("contacts", [])]:
                logging.info("user = %s was already a friend" % contactid)
                body["desc"] = self.ADDTYPE_OK
                self.write(body)
                self.finish()
                return

            #if already add the contact, but reply was not received, notify contact again, Hi guy, accept my friendship
            if contactid in [x.get("id", "") for x in user.get("appendings", [])]:
                logging.info("user = %s was already a pending friend" % contactid)
                body["desc"] = self.ADDTYPE_AUTH
                notify["desc"] = self.ADDTYPE_AUTH
                publish.publish_one(contactid, notify)
                self.write(body)
                self.finish()
                return
                
            # check the friendship, is user already added by the contact
            already_added_by_friend = 0

            if contact:
                if userid in [x.get("id", "") for x in contact.get("contacts", [])]:
                    logging.info("%s was already added by %s" % (userid, contactid))
                    already_added_by_friend = 1
                elif userid in [x.get("id", "") for x in contact.get("appendings", [])]:
                    logging.info("%s was already invited by %s" % (userid, contactid))
                    already_added_by_friend = 1
                    yield coll.find_and_modify({"id":contactid}, 
                                               {
                                                 "$pull":{"appendings":{"id":userid}},
                                                 "$push":{"contacts":{"id":userid, "nickname":user_nick, "type":contact_type}},
                                                 "$set": {"flag":change_flag},
                                                 "$unset": {"garbage": 1}
                                               })
                else:
                    pass

            is_mydevice = False
            if contact_type == self.USERTYPE_TERMINAL:
                is_mydevice = yield self.check_device(contactid, userid)

            is_bindadd = True if addtype == "bind" else False

            # begin to add friend
            if already_added_by_friend or is_bindadd or is_mydevice:
                #just add to contact
                notify["desc"] = self.ADDTYPE_OK
                body["desc"] = self.ADDTYPE_OK
                yield coll.find_and_modify({"id":userid}, 
                                           {
                                             "$push":{"contacts":{"id":contactid, "nickname":contact_nick, "type":contact_type}}, 
                                             "$set": {"flag":change_flag},
                                             "$unset": {"garbage": 1}
                                           })
            else:
                notify["desc"] = self.ADDTYPE_AUTH
                body["desc"] = self.ADDTYPE_AUTH
                yield coll.find_and_modify({"id":userid}, 
                                           {
                                             "$push":{"appendings":{"id":contactid, "nickname":contact_nick, "action":"offer"}}, 
                                             "$set": {"flag":change_flag}, 
                                             "$unset": {"garbage": 1}
                                           })

            # notify the user who was added as a friend
            publish.publish_one(contactid, notify)
            body["contactid"] = contactid
            self.write(body)
            self.finish()
        else:
            logging.error("invalid userid = %s , contact = %s" % (userid, contactid))
            self.set_status(404)
            self.write({"error":"not found"});
            self.finish()

    @tornado.gen.coroutine
    def check_device(self, userid, deviceid):
        conn = yield get_mysqlcon('mxsuser')
        if not conn:
            logging.error("connect to mysql failed")
            return False

        try:
            cur = conn.cursor()
            yield cur.execute(_checkdevice_sql, (deviceid, userid))
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            logging.error("oper db failed {0}".format(e))
            return False
        finally:
            conn.close()

