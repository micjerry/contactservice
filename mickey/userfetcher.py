import tornado.web
import tornado.httpclient
import logging
import redis
import json

import motor
from redis.sentinel import Sentinel

sentinel = Sentinel([('localhost', 26379)], socket_timeout=1)
db = motor.MotorClient("mongodb://localhost:27017").contact

@tornado.gen.coroutine
def getuser(token):
    user = None
    userid = None
    try:
        slave = sentinel.slave_for('master', socket_timeout=0.5)
        user = slave.get(token)
    except Exception as e:
        logging.error("can not get cached information {0}".format(e))

    if not user:
        httpclient = tornado.httpclient.AsyncHTTPClient()
        url = "http://localhost:8900/cxf/security/tokens?jsessionid=%s" % token
        session = "JSESSIONID=%s" % token
        ath_headers = {
          "Cookie" : session
        }

        res_body = {}
        try:
            response = yield httpclient.fetch(url, None, method = "GET", headers = ath_headers, body = None, follow_redirects = True)
            if response.code != 200:
                logging.error("get userinfo %d received session = %s" % (response.code, token))
                return userid

            res_body = json.loads(response.body.decode("utf-8"))
        except Exception as e:
            logging.error("get user info failed {0}".format(e))
            return userid

        userid = str(res_body.get("userID", ""))

        if not userid:
            logging.error("get userid failed session = %s" % token)
            return userid

        logging.info("get user id success token = %s id = %s" % (token, userid))
        #cach token
        try:
            master = sentinel.master_for('master', socket_timeout=0.1)
            master.set(token, userid)
            master.expire(token, 3600)
        except Exception as e:
            logging.error("can not cach user information {0}".format(e))

    else:
        userid = user.decode("utf-8") 
        
    return userid        

@tornado.gen.coroutine
def getcontact(contactid):
    httpclient = tornado.httpclient.AsyncHTTPClient()
    url = "http://localhost:9080/cxf/security/contacts/%s" % contactid

    res_body = {}
    try:
        response = yield httpclient.fetch(url, None, method = "GET", headers = {}, body = None)
        if response.code != 200:
            logging.error("get contactinfo failed userid = %s" % contactid)
            return res_body
        res_body = json.loads(response.body.decode("utf-8"))
    except Exception as e:
        logging.error("get userinfo failed {0}".format(e))

    return res_body
