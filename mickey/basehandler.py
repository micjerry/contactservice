import tornado.web
import tornado.gen

import logging

import mickey.userfetcher


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.p_userid = ""
        
    @tornado.gen.coroutine
    def prepare(self):
        token = self.request.headers.get("Authorization", "")

        logging.info("request receive with auth = %s" % token)
        if not token:
            logging.error("no token was found")
            self.send_error(502)
            return

        self.p_userid = yield mickey.userfetcher.getuser(token)
        
        if not self.p_userid:
            logging.error("auth failed with token %s" % token)
            self.send_error(502)
            return
            
