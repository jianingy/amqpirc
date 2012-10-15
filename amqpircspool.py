#!/usr/local/bin/python
#####################################################################
# amqpircspool.py is a part of amqpirc which is an AMQP to IRC proxy.
#
# amqpircbot.py is the IRC bot which connects to the specified IRC
# server and outputs messages from the specified spool path.
# 
# amqpircspool.py is the AMQP client which connects to AMQP/RabbitMQ
# and listens to the specified exchange, writing messages to the
# specified spool path.
#
# README and the latest version of the script can be found on Github:
# https://github.com/tykling/amqpirc
#####################################################################

### Load libraries
import os
import pika
import sys
import time
import tempfile
from optparse import OptionParser

### define and handle command line options
use = "Usage: %prog [-s amqpserver -u amqpuser -p amqppass -e amqpexchange -r routingkey]"
parser = OptionParser(usage = use)
parser.add_option("-H", "--amqphost", dest="server", metavar="server", default="localhost", help="The AMQP/RabbitMQ server hostname or IP (default: 'localhost')")
parser.add_option("-u", "--amqpuser", dest="user", metavar="user", help="The AMQP username")
parser.add_option("-p", "--amqppass", dest="password", metavar="password", help="The AMQP password")
parser.add_option("-e", "--amqpexchange", dest="exchange", metavar="exchange", default="myexchange", help="The AMQP exchange name (default 'myexchange')")
parser.add_option("-r", "--routingkey", dest="routingkey", metavar="routingkey", default="#", help="The AMQP routingkey (default '#')")
parser.add_option("-s", "--spoolpath", dest="path", metavar="path", default="/var/spool/amqpirc/", help="The spool path (default '/var/spool/amqpirc')")
options, args = parser.parse_args()

### Function to output to the console with a timestamp
def consoleoutput(message):
    print " [%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),message)

### Check access to spool path options.path
if not os.access(options.path, os.R_OK) or not os.access(options.path, os.W_OK):
    consoleoutput("Spool path %s is not readable or writable, bailing out" % options.path)
    sys.exit(1)

### Connect to ampq and open channel
connection = pika.BlockingConnection(pika.ConnectionParameters(host=options.server,credentials=pika.PlainCredentials(options.user, options.password)))
channel = connection.channel()

### Declare exchange
channel.exchange_declare(exchange=options.exchange,type='topic',passive=True, durable=True, auto_delete=False)

### Declare queue and get unique queuename
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

### Bind queue to exchange with the wildcard routing key #
channel.queue_bind(exchange=options.exchange,queue=queue_name,routing_key='#')
consoleoutput("Waiting for messages matching routingkey %s. To exit press CTRL+C" % options.routingkey)

### This function is called whenever a message is received
def process_message(ch, method, properties, body):
    fd, filename = tempfile.mkstemp(dir=options.path)
    f = os.fdopen(fd, 'wt')
    f.write(method.routing_key+'\n')
    f.write(body)
    f.close
    consoleoutput("Message written to spool file %s with routingkey %s:" % (filename,method.routing_key))
    print body

### Register callback function process_message to be called when a message is received
channel.basic_consume(process_message,queue=queue_name,no_ack=True)

### Loop waiting for messages
channel.start_consuming()