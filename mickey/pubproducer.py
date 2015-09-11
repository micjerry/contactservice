import pika
import json
import logging
from pika.adapters.tornado_connection import TornadoConnection

class PubProducer(object):

    def __init__(self, **kwargs):
        self._channel = None
        self._connection = None
        self._messages = []
        self._isclosing = False

        self._exchange = kwargs.get("exchange", "")

    def start(self):
        logging.debug("pikapublish begin initialcon")

        if not self._isclosing:
            credentials = pika.PlainCredentials('guest', 'guest')
            parameters =  pika.ConnectionParameters('localhost', credentials=credentials)
            try:
                self._connection = TornadoConnection(parameters, on_open_callback = self.on_connected)
            except Exception as e:
                logging.error("connect to rabbitmq failed {0}".format(e))

    def on_connected(self, connection):
        logging.debug("pikapublish begin on_connected")
        self._connection = connection
        self._connection.add_on_close_callback(self.on_connection_closed)
        try:
            self._connection.channel(self.on_channel_open)
        except Exception as e:
            logging.error("open channel failed {0}".format(e))

    def on_connection_closed(self, connection, reply_code, reply_text):
        logging.info("connection closed")
        if self._isclosing:
            return

        logging.error("Connection closed, reopening in 5 seconds: (%s) %s" % (reply_code, reply_text))
        self._connection.add_timeout(5, self.start)
    
    def on_channel_closed(self, channel, reply_code, reply_text):
        if self._isclosing:
            return

        logging.error("Channel %i was closed: (%s) %s" % (channel, reply_code, reply_text))
        if self._connection and self._connection.is_open:
            try:
                self._connection.channel(self.on_channel_open)
            except Exception as e:
                logging.error("open channel failed {0}".format(e))

    def on_channel_open(self, channel):
        logging.debug("pikapublish begin on_channel_open")
        self._channel = channel
        self.publishmsg()
        
    def on_queue_declared(self, frame, receiver, notify):
        logging.debug("pikapublish begin on_queue_declared %s %r" % (receiver, notify))
        noti_body = json.dumps(notify)
        try:
            self._channel.basic_publish(exchange = self._exchange,
                                       routing_key = receiver,
                                       body = noti_body)
        except Exception as e:
            logging.error("pikapublish publish exception {0}".format(e))


    def pushmsg(self, user, body):
        logging.debug("pikapublish begin pushmsg %r  %s" % (body, user))
        if not user or not body or self._isclosing:
            return
        
        self._messages.append({"user":user, "body":body})

        if self._channel:
            self._connection.add_timeout(1, self.publishmsg)
        else:
            self.start()

    def close(self):
        self._isclosing = True
        if self._connection:
            self._connection.close()

    def publishmsg(self):
        logging.debug("pikapublish begin to publishmsg")

        for item in self._messages:
            user = item.get("user", "")
            body = item.get("body", "")
            
            if not isinstance(user, str) and not isinstance(user, bytes):
                logging.error("invalid user %r not string" % user)    
                continue

            if "pub" in user or "temp" in user:
                noti_body = json.dumps(body)
                try:
                    logging.info("publish %s" % user)
                    self._channel.basic_publish(exchange = self._exchange,
                                               routing_key = user,
                                               body = noti_body)
                    continue
                except Exception as e:
                    logging.error("pikapublish publish to subs exception {0}".format(e))

            else:
                try:
                    self._channel.queue_declare(queue=user, callback = lambda frame, receiver=user, notify=body:self.on_queue_declared(frame, receiver, notify))
                except Exception as e:
                    logging.error("pikapublish queue_declare catch exception {0}".format(e))            


        self._messages[:] = []
    
