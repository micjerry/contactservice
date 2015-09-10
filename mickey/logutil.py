import os
import sys
import logging

import tornado.httpserver

def setuplog():
    log_path = "/var/log/" + sys.argv[0].replace(".py", "")
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    path = lambda *a:os.path.join(log_path, *a)

    #setup access log
    access_log = logging.getLogger("tornado.access")
    access_log.setLevel(logging.DEBUG)
    accessHandler = logging.handlers.RotatingFileHandler(
      path('access.log'), maxBytes=50000000, backupCount=5)
    access_log.addHandler(accessHandler)

    #setup app log
    app_log = logging.getLogger("tornado.application")
    app_log.setLevel(logging.DEBUG)
    appHandler = logging.handlers.RotatingFileHandler(
      path('app.log'),  maxBytes=50000000, backupCount=5)
    app_log.addHandler(appHandler)

    #setup gen log
    gen_log = logging.getLogger("tornado.general")
    gen_log.setLevel(logging.DEBUG)
    genHandler = logging.handlers.RotatingFileHandler(
      path('gen.log'),  maxBytes=50000000, backupCount=5)
    gen_log.addHandler(genHandler)

    #setup service log
    service_log = logging.getLogger('')
    service_log.setLevel(logging.DEBUG)
    serviceHandler = logging.handlers.RotatingFileHandler(
      path('service.log'),  maxBytes=50000000, backupCount=5)
    formatter = logging.Formatter('%(pathname)s %(filename)s %(funcName)s %(lineno)d %(asctime)s %(levelname)s %(message)s')
    serviceHandler.setFormatter(formatter)
    service_log.addHandler(serviceHandler)

