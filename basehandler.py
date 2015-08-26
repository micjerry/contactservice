import tornado.web
import tornado.gen

import json
import redis
import motor
import logging

import tornado.httpclient

r = redis.StrictRedis(host='localhost', port=6379, db=0)

class BaseHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.p_userid = ""
        
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
            user = r.get(token)
            if not user:
                #get user
                httpclient = tornado.httpclient.AsyncHTTPClient()
                url = "http://localhost:9080/cxf/security/tokens;jsessionid=%s" % token
                session = "JSESSIONID=%s" % token
                ath_headers = {
                  "Cookie" : session
                }

                response = yield httpclient.fetch(url, None, method = "GET", headers = ath_headers, body = None, follow_redirects = True)

                if response.code != 200:
                    logging.error("get userinfo %d received session = %s" % (response.code, token))
                    self.send_error(502)
                    return

                res_body = {}
                try:
                    res_body = json.loads(response.body.decode("utf-8"))
                except Exception as e:
                    logging.error("invalid body received")
                    self.send_error(502)
                    return

                nickname = res_body.get("commName", "")
                sign = res_body.get("sign", "")
                self.p_userid = str(res_body.get("userID", ""))	
                name = res_body.get("name", "")

                logging.info("get auth userid = %s nickname = %s sign = %s" % (self.p_userid, nickname, sign))
                if not self.p_userid:
                    logging.error("get userid failed session = %s" % token)
                    self.send_error(502)
                    return

                #cach token
                r.set(token, self.p_userid)
                r.expire(token, 3600)

                #update user info
                modresult = yield coll.find_and_modify(
                    {"id":self.p_userid},
                    {"$set":
                        {
                          "nickname":nickname,
                          "sign":sign,
                          "name":name
                        }
                    },
                    True
                )
                if modresult:
                    logging.info("find and match")

            else:
                self.p_userid = user.decode("utf-8")

                
