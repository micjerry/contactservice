import tornado.web
import tornado.gen
import json
import io
import logging

import motor
import tornado_mysql

from mickey.mysqlcon import get_mysqlcon

import mickey.userfetcher
from mickey.basehandler import BaseHandler

_query_sql = """
  SELECT comdesc FROM combs WHERE name = %s;
"""

class DisplayCombHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        comname = data.get("name", "")

        logging.info("list contact for %s" % comname)

        if not comname:
            logging.error("invalid parameter")
            self.set_status(403)
            self.finish()
            return

        comdesc = yield self.fetch_com(comname)
        if not comdesc:
            logging.error("user %s was not found" % userid)
            self.set_status(404)
            self.finish()
            return

        self.set_status(200)
        self.write({"desc":comdesc})
        self.finish()

    @tornado.gen.coroutine
    def fetch_com(self, comname):
        conn = yield get_mysqlcon()
        if not conn:
            logging.error("connect to mysql failed")
            self.set_status(403)
            self.finish()
            return ""

        try:
            cur = conn.cursor()
            yield cur.execute(_query_sql, (comname))
            device = cur.fetchone()
            cur.close()
            return device[0]
        except Exception as e:
            logging.error("db oper failed {0}".format(e))
            return {}
        finally:
            conn.close()

