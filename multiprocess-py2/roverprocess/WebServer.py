# Rover Modules
from RoverProcess import RoverProcess
from threading import Thread
from multiprocessing import BoundedSemaphore

# WebUI Modules
from WebUI import bottle
from WebUI.bottle import run, ServerAdapter
from WebUI.Routes import WebServerRoutes

# Python Modules
import time
import json
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

class WebServer(RoverProcess):

	## Replaces the stock WSGI server with one that we can control within
	##	the context of the rover software
	class RoverWSGIServer(ServerAdapter):

		def run(self, app):  # pragma: no cover
			from wsgiref.simple_server import make_server
			from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
			import socket

			class FixedHandler(WSGIRequestHandler):
				def address_string(self):  # Prevent reverse DNS lookups please.
					return self.client_address[0]

				def log_request(*args, **kw):
					if not self.quiet:
						return WSGIRequestHandler.log_request(*args, **kw)

			handler_cls = self.options.get('handler_class', FixedHandler)
			server_cls = self.options.get('server_class', WSGIServer)

			if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
				if getattr(server_cls, 'address_family') == socket.AF_INET:

					class server_cls(server_cls):
						address_family = socket.AF_INET6

			self.srv = make_server(self.host, self.port, app, server_cls,
								   handler_cls)
			self.port = self.srv.server_port
			self.srv.serve_forever()
				
	def setup(self, args):
		self.dataSem = BoundedSemaphore()
		self.data = {}
		self.routes = WebServerRoutes(parent=self, dataSem=self.dataSem)
		
		bottle.TEMPLATE_PATH = ['./WebUI/views']
		print "Web Templates Loaded From:", bottle.TEMPLATE_PATH
		
		self.server = self.RoverWSGIServer(host='localhost', port=80)
		Thread(target = self.startBottleServer).start()
		
	def loop(self):
		#self.setShared("TestData", "hi!")
		time.sleep(1)

	def messageTrigger(self, message):
		RoverProcess.messageTrigger(self, message)
		#print message
		with self.dataSem:
			self.data.update(message)

	def cleanup(self):
		RoverProcess.cleanup(self)

	## Bottle server code running in independent thread
	# Please see routes.py for information about exchanging data
	def startBottleServer(self):
		run(server=self.server, app=self.routes.instance)
