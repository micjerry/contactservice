from pika import adapters
import pika
import logging

class SubConnection(object):
    def __init__(self, amqp_url):
        self._connection = None
        self._url = amqp_url
        self._closing = False
        self._cosumers = []
        self._limits = 60000

    def start(self):
        self._connection = self.connect()

    def connect(self):
        logging.info("Connecting to %s" % self._url)
        return adapters.TornadoConnection(pika.URLParameters(self._url),
                                          self.on_connection_open)

    def add_on_connection_close_callback(self):        
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        logging.info("connection closed")
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logging.error("Connection closed, reopening in 5 seconds: (%s) %s" % (reply_code, reply_text))
            self._connection.add_timeout(5, self.reconnect)

    def on_connection_open(self, unused_connection):
        logging.info('Connection opened %d ' % len(self._cosumers) )
        self.add_on_connection_close_callback()
        return list(map(lambda x: x.connect(), self._cosumers))
        
        
    def reconnect(self):
        if not self._closing:
            self._connection = self.connect()
        
    def isconnected(self):
        return False if not self._connection else self._connection.is_open

    def isclosing(self):
        return self._closing

    def checkconsumers(self):
        self._cosumers = list(filter(lambda x: not x.isclosed(), self._cosumers))

    def stop(self):
        logging.info("Connection stopped")
        self._closing = True
        map(lambda x: x.close(), self._cosumers)
        self._connection.close()

    def islimited(self):
        return len(self._cosumers) > self._limits

    def addconsumer(self, consumer):
        logging.info("consumer added")
        self._cosumers.append(consumer)
        
