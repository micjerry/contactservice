import pika
import json
import logging
from pika.adapters.tornado_connection import TornadoConnection

class LoginPublish(object):

    def __init__(self):
        self.channel = None
        self.connection = None
        self.messages = []

    def initialcon(self):
        logging.debug("pikapublish begin initialcon")
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters =  pika.ConnectionParameters('localhost', credentials=credentials)
        self.connection = TornadoConnection(parameters, on_open_callback = self.on_connected)

    def on_connected(self, connection):
        logging.debug("pikapublish begin on_connected")
        self.connection = connection
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, channel):
        logging.debug("pikapublish begin on_channel_open")
        self.channel = channel
        self.publishmsg()
        
    def releasecon(self):
        if self.connection:
            self.connection.close()

    def pushmsg(self, loginkey, body):
        logging.debug("begin pushmsg %r  %s" % (body, loginkey))
        if not loginkey or not body:
            return

        self.messages.append({"key":loginkey, "body":body})
        self.publishmsg()

    def publishmsg(self):
        logging.debug("begin to publishmsg")
        if not self.channel:
            logging.debug("begin to open channel")
            self.initialcon()
            return

        for item in self.messages:
            key = item.get("key", "")
            body = item.get("body", "")

            logging.debug("begin to publish %s body = %r" % (key, body))
            if not isinstance(key, str) and not isinstance(key, bytes):
                logging.error("invalid key")
                continue

            noti_body = json.dumps(body)
            try:
                self.channel.basic_publish(exchange = 'pclogin',
                                           routing_key = key,
                                           body = noti_body)
            except Exception as e:
                logging.error("pikapublish  catch exception {0}".format(e))


        self.messages[:] = []
 
