import tornado.web
import tornado.gen
import json
import io
import logging

import motor

class AddContactHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        coll = self.application.db.users
        publish = self.application.publish

        #get parameters of request
        data = json.loads(self.request.body.decode("utf-8"))
        userid = data.get("id", "invalid")
        contactid = data.get("contactid", "invalid")
        contact_type = data.get("type", "person")
        user_nick = data.get("nickname", "")
        contact_nick = data.get("contactnick", "")
        comment = data.get("comment", "")

        logging.info("begin to handle add contact request, userid = %s contact = %s type = %s nick = %s cnick = %s" % (userid, contactid, contact_type, user_nick, contact_nick))

        #check parameters        
        user = yield coll.find_one({"id":userid})
        contact = yield coll.find_one({"id":contactid})
        if (user and contact):

            # notify 
            notify = {
              "name": "mx.contact.add_contact",
              "userid": userid,
              "comment": comment
            }

            # check is repeat add
            already_add = 0
            contacts = user.get("contacts", [])
            appendings = user.get("appendings", [])

            for friend in contacts:
                if (friend["id"] == contactid):
                    logging.info("user = %s was already a friend" % contactid)
                    already_add = 1
                    break

            for appending in appendings:
                if (appending["id"] == contactid):
                    logging.info("user = %s was already a pending friend" % contactid)
                    already_add = 1
                    #notify contact again, Hi guy, accept my friendship
                    publish.publish_one(contactid, notify)
                    break

            if already_add:
                # already added do nothing
                self.finish()
                return
            else:
                # device just save 
                if contact_type == "device":
                    # just add, no notify
                    yield coll.find_and_modify({"id":userid}, {"$push":{"contacts":{"id":contactid, "type":contact_type, "nickname": contact_nick}}})
                    self.finish()
                    return
                else:
                    contact_type = "person"
                
                # is user  already added by the contact
                already_added_by_friend = 0
                friend_contacts = contact.get("contacts", [])
                friend_appendings = contact.get("appendings", [])

                for befriend in friend_contacts:
                    if (befriend["id"] == userid):
                        logging.info("%s was already added by %s" % (userid, contactid))
                        already_added_by_friend = 1
                        break

                if not already_added_by_friend:
                    # check appendings
                    for beappending in friend_appendings:
                        if (beappending["id"] == userid): 
                            logging.info("%s was already invited by %s" % (userid, contactid))
                            already_added_by_friend = 1
                            #move userid appendings to contacts
                            yield coll.find_and_modify({"id":contactid}, {"$pull":{"appendings":{"id":userid}}})
                            yield coll.find_and_modify({"id":contactid}, {"$push":{"contacts":{"id":userid, "nickname":user_nick, "type":contact_type}}})
                            break                

                # begin to add friend
                if already_added_by_friend:
                    #just add to contact
                    yield coll.find_and_modify({"id":userid}, {"$push":{"contacts":{"id":contactid, "nickname":contact_nick, "type":contact_type}}})
                else:
                    #add to appendings, need to be agree by friend
                    yield coll.find_and_modify({"id":userid}, {"$push":{"appendings":{"id":contactid, "nickname":contact_nick}}})


            # notify the user who was added as a friend
            publish.publish_one(contactid, notify)
        else:
            logging.error("invalid userid = %s , contact = %s" % (userid, contactid))
            self.set_status(404)
            self.write({"error":"not found"});

        self.finish()
