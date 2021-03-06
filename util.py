def gethostname(mdsip):
	'mdsip: the IP address of MDS'
	import socket
	s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect((mdsip, 12345))
	hostname=s.getsockname()[0]
	s.close()
	return hostname

class Object:
	def __init__(self, d=None):
		if isinstance(d, dict):
			self.__dict__=d

def message2object(message):
	"receive a PB message, returns its guid and a object describing the message"
	import guid as Guid, messages_pb2 as msg
	if not hasattr(message, 'ListFields'):
		return message
	fields=message.ListFields()
	rst=Object()
	for f in fields:
		name=f[0].name
		value=f[1]
		if isinstance(value, msg.Guid):
			value=Guid.toStr(value)
		elif hasattr(value, 'ListFields'):
			value=message2object(value, '')
		elif hasattr(value, '_values'):
			value=[message2object(x) for x in value._values]
		else:
			pass  #should be a native value like str, int, float, ...			
		setattr(rst, name, value)
	return rst

def object2message(object, message):
	import guid as Guid, messages_pb2 as msg
	d = object if isinstance(object, dict) else object.__dict__
	for key in d:
		if key.startswith('_'):
			continue
		value=d[key]
		if isinstance(value, list):
			mfield=getattr(message, key)
			appender = (lambda x : mfield.append(x)) if hasattr(mfield, 'append') \
				  else (lambda x : object2message(x, mfield.add()))
			for item in value:
				appender(item)
		else:
			try:
				if key == 'guid':
					value=Guid.fromStr(value)
					Guid.assign(message.guid, value)
				else:
					setattr(message, key, value)
			except:
				print 'exception occured'
				pass

def setupLogging(configure):
	import logging, os, os.path
	str2logginglevel={\
		'debug'		: logging.DEBUG,\
		'info'		: logging.INFO,\
		'warning'	: logging.WARNING,\
		'warn'		: logging.WARNING,\
		'error'		: logging.ERROR,\
		'fatal'		: logging.CRITICAL,\
	}
	loglevel=configure['logging-level']
	assert loglevel in str2logginglevel, 'invalid logging level "{0}"'.format(level)
	loglevel=str2logginglevel[loglevel]

	logfile=configure['logging-file']
	if logfile=='stdout':
		logfile=None
	else:
		assert not logfile[-1] in ['/', '\\'], 'logging-file must NOT be a directory'
		directory=os.path.dirname(logfile)
		if not os.path.isdir(directory):
			os.makedirs(directory)
	logging.basicConfig(filename=logfile, level=loglevel)


class Pool:
	def __init__(self, constructor, destructor=None):
		self.pool={}
		self.ctor=constructor
		if isinstance(destructor, str):
			destructor=getattr(constructor, destructor)
		self.dtor=destructor
	def get(self, *key):
		if key in self.pool:
			return self.pool[key]
		value=self.ctor(*key)
		self.pool[key]=value
		return value
	def dispose(self):
		if self.dtor:
			for value in self.pool.itervalues():
				self.dtor(value)
		self.pool.clear()

def testPool():
	class Stub:
		def __init__(self,a,b,c,d):
			self.key=(a,b,c,d)
			print 'constructing stub', self.key
		def close(self):
			print 'destructing stub', self.key
	pool=Pool(Stub)
	pool.get(10,20,3,2)
	pool.get(32,1.2312,56,32)
	pool.get('asdf', 'jkl;', 32, 3.13)
	pool.dispose()	

	class Socket:
		def __init__(self,endpoint):
			self.key=endpoint
			print 'constructing socket', self.key
		def close(self):
			print 'destructing socket', self.key
	pool=Pool(lambda *args : Socket(args), Socket.close)
	pool.get(10,20)
	pool.get(32,1.2312)
	pool.get('asdf', 'jkl;')
	pool.dispose()


if __name__ == '__main__':
	#print gethostname('localhost.localdomain')
	testPool()
