import pika
import logging
from pika.adapters.tornado_connection import TornadoConnection
from mickey.subconnectionmgr import SubConnectionMgr
from mickey.subconnection import SubConnection

class PikaConsumer(object):

    EXCHANGE = 'user'
    EXCHANGE_TYPE = 'direct'

    def __init__(self, userid):
        self._userid = userid
        
        #websocket connection
        self._closing = False
        self._pubsub = None
        self._pikaclient = None
        self._channel = None
        self._consumers = []

    def start(self):
        logging.debug("start consumer %s " % self._userid)

        # get one rabbitmq connection
        self._pikaclient = SubConnectionMgr.connection()
        if self._pikaclient:
            self._pikaclient.addconsumer(self)

        #create the channel if the connection is opened
        if self._pikaclient.isconnected():
            self.connect()
        else:
            logging.debug("pika is not connected")
            
        
    def connect(self):
        logging.debug("begin connect channel %s" % self._userid)

        #clear all the consumers before connect
        del self._consumers[:]

        self._pikaclient._connection.channel(self.on_channel_open)

    def on_channel_closed(self, channel, reply_code, reply_text):
        #closed normal do nothing
        if self._closing:
            return

        logging.error("Channel %i was closed: (%s) %s" % (channel, reply_code, reply_text))
        #closed by pika, we will recreate the channel
        if not self._pikaclient.isclosing() and self._pikaclient.isconnected():
            self.connect()

    def on_channel_open(self, channel):
        logging.debug("on_channel_open %s" % self._userid)
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        try:
            self._channel.exchange_declare(exchange = self.EXCHANGE,
                                          exchange_type = self.EXCHANGE_TYPE,
                                          auto_delete = False,
                                          durable = False,
                                          callback = self.on_exchange_declared)
        except Exception as e:
            logging.error("exchange_declare error {0}".format(e))

    def on_exchange_declared(self, frame):
        logging.debug("begin on_exchange_declared %s" % self._userid)
        try:
            #declare queue
            if self._pubsub._queuename:
                self._channel.queue_declare(auto_delete = False,
                                            queue = self._pubsub._queuename,
                                            durable = False,
                                            exclusive = False,
                                            callback = self.on_queue_declared)
            #declare temp queue
            if self._pubsub._tmp_queuename:
                self._channel.queue_declare(auto_delete = False,
                                            queue = self._pubsub._tmp_queuename,
                                            durable = False,
                                            exclusive = True,
                                            callback = self.on_tmp_queue_declared)
        except Exception as e:
            logging.error("queue_declare error {0}".format(e))

    def on_queue_declared(self, frame):
        logging.debug("begin on_queue_declared %s" % self._userid)
        for item in self._pubsub._routings:
            try:
                logging.info("bind %s" % item)
                self._channel.queue_bind(exchange = self.EXCHANGE,
                                         queue = self._pubsub._queuename,
                                         routing_key = item,
                                         callback = self.on_queue_bound)
            except Exception as e:
                logging.error("queue_bind error {0}".format(e))

    def on_queue_bound(self, frame):
        logging.debug("begin on_queue_bound %s" % self._userid)
        try:
            consumer = self._channel.basic_consume(consumer_callback = self.on_pika_message,
                                                   queue = self._pubsub._queuename,
                                                   no_ack = True)
            self._consumers.append(consumer)
        except Exception as e:
            logging.error("cosume error {0}".format(e))

    def on_tmp_queue_declared(self, frame):
        logging.debug("begin on_tmp_queue_declared %s" % self._userid)
        for item in self._pubsub._tmp_routings:
            try:
                logging.info("bind %s" % item)
                self._channel.queue_bind(exchange = self.EXCHANGE,
                                        queue = self._pubsub._tmp_queuename,
                                        routing_key = item,
                                        callback = self.on_tmp_queue_bound)
            except Exception as e:
                logging.error("queue_bind error {0}".format(e))

    def on_tmp_queue_bound(self, frame):
        logging.debug("begin on_tmp_queue_bound %s" % self._userid)
        try:
            consumer = self._channel.basic_consume(consumer_callback = self.on_tmp_pika_message,
                                                   queue = self._pubsub._tmp_queuename,
                                                   no_ack = True)
            self._consumers.append(consumer)
        except Exception as e:
            logging.error("cosume error {0}".format(e))

    def on_pika_message(self, channel, method, header, body):
        logging.debug("begin on_pika_message %s %r" % (self._userid, body))
        if self._pubsub:
            self._pubsub.add_msg(body)
            
    def on_tmp_pika_message(self, channel, method, header, body):
        logging.debug("begin on_tmp_pika_message %s %r" % (self._userid, body))
        if self._pubsub:
            self._pubsub.add_tmpmsg(body)        

    def on_consumer_cancelled(self, method_frame):
        logging.info("consumer cancelled %s" % self._userid)
        #close normal do nothing
        if self._closing:
            return

        #cancelled by the pika, we will close the channel
        if self._channel:
           self._channel.close()

    def close(self):
        #close normal when user offline
        self._closing = True
        self._pubsub = None

        #cancel all the consumers
        for item in self._consumers:
            self._channel.basic_cancel(consumer_tag = item)

        del self._consumers[:]

        #close channel
        if self._channel:
            self._channel.close()

    def isclosed(self):
        return self._closing
