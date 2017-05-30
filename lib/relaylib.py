# coding=utf-8
"""
lib that handles the communication between the rpi and the relay mbed
"""
import platform
from functools import partial
from threading import Thread
from time import sleep

from os.path import getsize

import serial.tools.list_ports
from serial import Serial


def _int_to_bytes(number):
	return "".join([chr(number >> i & 0xff) for i in (24, 16, 8, 0)])


def find_device(ID):
	# comports = serial.tools.list_ports.comports()
	comports = serial.tools.list_ports.comports()
	for port in comports:
		if platform.system() == 'Windows':
			if ID.upper() in port.hwid.upper():
				# logger.debug('found device at: ' + port.device)
				return port.device
		else:
			if ID.upper() in port[2].upper():
				# logger.debug('found device at: ' + port[0])
				return port[0]


class Relay(object):
	"""
	class that handles the communication between the rpi and the relay mbed
	"""
	_ACK = 'ACK'
	_VOLUME = 'SET_VOLUME'
	_SEND_FILE = 'SEND_FILE'
	_PLAY_LAST = "PLAY_LAST"
	_packet_types = {
		_SEND_FILE: chr(0b00001111),
		_VOLUME: chr(0b00110011),
		_PLAY_LAST: chr(0b10001011),
		_ACK: chr(0b11111111)
	}

	def __init__(self, port, baudrate):
		self._s = Serial(port=port, baudrate=baudrate)
		if self._s.isOpen():
			self._s.close()
			self._s.open()

		self._thread = Thread()
		self._stopping = False

	def join(self):
		"""
		wait until the thread is done
		"""
		if self.is_busy():
			self._thread.join()

	def stop(self):
		"""
		stops the current action and waits until the thread exits
		"""
		self._stopping = True
		self.join()

	def is_busy(self):
		"""
		:return: is a transmission ongoing
		:rtype: bool
		"""
		return self._thread.isAlive()

	def send_file(self, path):
		"""
		send a file to the relay
		:param path: path to the file
		:type path: str
		"""
		self._start_thread(partial(self._send_file, path))

	def set_volume(self, value):
		"""
		send value to set de amplifier to
		:param value: 0-100
		:type value: int
		"""
		self._start_thread(partial(self._set_volume, value))

	def play_last(self):
		"""
		play the last file
		"""
		self._start_thread(self._play_last)

	def _start_thread(self, target):
		if self.is_busy():
			raise RuntimeError("still busy")
		else:
			self._stopping = False
			self._thread = Thread(target=target, name="relay")
			self._thread.setDaemon(True)
			self._thread.start()

	def _play_last(self):
		self._s.flushInput()
		self._s.write(self._packet_types[self._PLAY_LAST])
		self._s.flush()
		if not self._receive_ack():
			return

	def _send_file(self, path):
		with open(path, 'rb', -1) as f:  # -1 == io.DEFAULT_BUFFER_SIZE
			# send type
			self._s.flushInput()
			self._s.write(self._packet_types[self._SEND_FILE])
			self._s.flush()
			if not self._receive_ack():
				return

			sleep(1)  # give the mbed time to init sd and create file

			# send file size (4 bytes)
			size = getsize(path)
			for size_byte in _int_to_bytes(size):
				self._s.flushInput()
				self._s.write(size_byte)
				self._s.flush()
				if not self._receive_ack():
					return

			# send data in bulk of 64 bytes
			i = 0
			while not self._stopping:
				data = f.read(512)
				if data == "":
					break
				print i
				i += 1
				self._s.flushInput()
				self._s.write(data)
				self._s.flush()
				if not self._receive_ack():
					return

	def _receive_ack(self):
		# todo timeout
		print "wait on ack"
		read = self._s.read(1)
		ack = (read == self._packet_types[self._ACK])
		if not ack:
			print ord(read)
		else:
			print "got ack"
		return ack

	def _set_volume(self, value):
		# send type
		self._s.flushInput()
		self._s.write(self._packet_types[self._VOLUME])
		self._s.flush()
		if not self._receive_ack():
			return

		# send value
		self._s.flushInput()
		self._s.write(chr(value))
		self._s.flush()
		if not self._receive_ack():
			return


if __name__ == '__main__':
	relay = Relay("COM3", 115200)
	# relay.set_volume(10)
	# relay.send_file("D:/Desktop/test.wav")
	relay.play_last()
	relay.join()
