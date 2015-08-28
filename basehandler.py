import tornado.web
import tornado.gen

import json
import redis

import motor
import logging

import tornado.httpclient

from redis.sentinel import Sentinel

sentinel = Sentinel([('localhost', 26379)], socket_timeout=0.1)

class BaseHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.p_userid = ""
        self.p_userinfo = {}
        
    @tornado.gen.coroutine
    def prepare(self):
        coll = self.application.db.users
        token = self.request.headers.get("Authorization", "")

        logging.info("request receive with auth = %s" % token)
        if not token:
            logging.error("no token was found")
            self.send_error(502)
            return
        else:
            user = ""
            # get cached user info
            try:
                slave = sentinel.slave_for('master', socket_timeout=0.1)
                user = slave.get(token)
            except Exception as e:
                logging.error("can not get cached information {0}".format(e))

            if not user:
                #get user
                yield self.getuser(token)

                if not self.p_userid:
                    logging.error("get user info failed")
                    self.send_error(502)
                    return

                logging.info("get auth userid = %s nickname = %s sign = %s" % (self.p_userid, self.p_userinfo["nickname"], self.p_userinfo["sign"]))
                if not self.p_userid:
                    logging.error("get userid failed session = %s" % token)
                    self.send_error(502)
                    return

                #cach token
                try:
                    master = sentinel.master_for('master', socket_timeout=0.1)
                    master.set(token, self.p_userid)
                    master.expire(token, 3600)
                except Exception as e:
                    logging.error("can not cach user information {0}".format(e))

                #update user info
                try:
                    modresult = yield coll.find_and_modify(
                        {"id":self.p_userid},
                        {"$set":
                            self.p_userinfo
                        },
                        True
                    )
                    logging.info("update user information successful")
                except Exception as e:
                    logging.error("can not update user information {0}".format(e))

            else:
                self.p_userid = user.decode("utf-8")

    @tornado.gen.coroutine
    def getuser(self, token):
        httpclient = tornado.httpclient.AsyncHTTPClient()
        url = "http://localhost:8900/cxf/security/tokens?jsessionid=%s" % token
        session = "JSESSIONID=%s" % token
        ath_headers = {
          "Cookie" : session
        }

        response = yield httpclient.fetch(url, None, method = "GET", headers = ath_headers, body = None, follow_redirects = True)

        if response.code != 200:
            logging.error("get userinfo %d received session = %s" % (response.code, token))
            return

        res_body = {}
        try:
            res_body = json.loads(response.body.decode("utf-8"))
        except Exception as e:
            logging.error("invalid body received")
            return

        self.p_userinfo["nickname"] = res_body.get("commName", "")
        self.p_userinfo["sign"] = res_body.get("sign", "")
        self.p_userid = str(res_body.get("userID", ""))
        self.p_userinfo["name"] = res_body.get("name", "")

