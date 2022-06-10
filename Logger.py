import sys
import time
from threading import Lock

lock = Lock()


def padd(n, i = 2):
	return str(n).zfill(i)


def datestring():
	t = time.localtime()
	return "%s-%s-%s | %s:%s:%s" % (padd(t.tm_mday), padd(t.tm_mon), padd(t.tm_year),
		padd(t.tm_hour), padd(t.tm_min), padd(t.tm_sec))


def log(text, name=""):
	lock.acquire()
	try:
		lines = text.split("\n")
		for line in lines:
			print("[%s]%s: %s" % (datestring(), name, line))
	except Exception:
		print("[%s]%s: %r" % (datestring(), name, text))
	lock.release()
	sys.stdout.flush()
