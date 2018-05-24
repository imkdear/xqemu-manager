#!/usr/bin/env python
#
# Simple manager prototype for xqemu
#
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox
from PyQt5.uic import loadUiType
from PyQt5 import QtCore, QtGui
import sys
import os, os.path
import json
import subprocess

SETTINGS_FILE = './settings.json'

# Load UI files
settings_class, _ = loadUiType('settings.ui')
mainwindow_class, _ = loadUiType('mainwindow.ui')

class SettingsManager(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.settings = {
			'xqemu_path': '/path/to/xqemu',
			'mcpx_path': '/path/to/mcpx.bin',
			'flash_path': '/path/to/flash.bin',
			'hdd_path': '/path/to/hdd.img',
			'hdd_locked': True,
			'dvd_present': True,
			'dvd_path': '/path/to/disc.iso',
			'short_anim': False,
		}

	def save(self):
		with open(SETTINGS_FILE, 'w') as f:
			f.write(json.dumps(self.settings, indent=2))

	def load(self):
		if os.path.exists(SETTINGS_FILE):
			with open(SETTINGS_FILE, 'r') as f:
				d = f.read()
			self.settings = json.loads(d)
		else:
			self.reset()

class SettingsWindow(QDialog, settings_class):
	def __init__(self, settings, *args):
		super(SettingsWindow, self).__init__(*args)
		self.settings = settings
		self.setupUi(self)

		# Little helper functions to hook up the gui to the model
		def setTextAttr(widget, var): self.settings.settings[var] = widget.text()
		def getTextAttr(widget, var): widget.setText(self.settings.settings[var])
		def setCheckAttr(widget, var): self.settings.settings[var] = widget.isChecked()
		def getCheckAttr(widget, var): widget.setChecked(self.settings.settings[var])

		def bindTextWidget(widget, var):
			getTextAttr(widget, var)
			widget.textChanged.connect(lambda:setTextAttr(widget, var))

		def bindCheckWidget(widget, var):
			getCheckAttr(widget, var)
			widget.stateChanged.connect(lambda:setCheckAttr(widget, var))

		def bindFilePicker(button, text):
			button.clicked.connect(lambda:self.setSaveFileName(text))

		bindTextWidget(self.xqemuPath, 'xqemu_path')
		bindFilePicker(self.setXqemuPath, self.xqemuPath)
		bindCheckWidget(self.useShortBootAnim, 'short_anim')
		bindCheckWidget(self.dvdPresent, 'dvd_present')
		bindTextWidget(self.dvdPath, 'dvd_path')
		bindFilePicker(self.setDvdPath, self.dvdPath)
		bindTextWidget(self.mcpxPath, 'mcpx_path')
		bindFilePicker(self.setMcpxPath, self.mcpxPath)
		bindTextWidget(self.flashPath, 'flash_path')
		bindFilePicker(self.setFlashPath, self.flashPath)
		bindTextWidget(self.hddPath, 'hdd_path')
		bindFilePicker(self.setHddPath, self.hddPath)
		bindCheckWidget(self.hddLocked, 'hdd_locked')

	def setSaveFileName(self, obj):
		options = QFileDialog.Options()
		fileName, _ = QFileDialog.getOpenFileName(self,
				"Select File",
				obj.text(),
				"All Files (*)", options=options)
		if fileName:
			obj.setText(fileName)

class Xqemu(object):
	def __init__(self):
		self._p = None

	def start(self, settings):
		def check_path(path):
			if not os.path.exists(path) or os.path.isdir(path):
				raise Exception('File %s could not be found!' % path)

		xqemu_path = settings.settings['xqemu_path']
		check_path(xqemu_path)
		mcpx_path = settings.settings['mcpx_path']
		check_path(mcpx_path)
		flash_path = settings.settings['flash_path']
		check_path(flash_path)
		hdd_path = settings.settings['hdd_path']
		check_path(hdd_path)
		short_anim_arg = ',short_animation' if settings.settings['short_anim'] else ''

		dvd_path_arg = ''
		if settings.settings['dvd_present']:
			check_path(settings.settings['dvd_path'])
			dvd_path_arg = ',file=' + settings.settings['dvd_path']

		# Build qemu lunch cmd
		cmd = '%(xqemu_path)s \
			-cpu pentium3 \
			-machine xbox,bootrom=%(mcpx_path)s%(short_anim_arg)s -m 64 \
			-bios %(flash_path)s \
			-net nic,model=nvnet -net user \
			-monitor stdio \
			-drive file=%(hdd_path)s,index=0,media=disk \
			-drive index=1,media=cdrom%(dvd_path_arg)s' % locals()

		self._p = subprocess.Popen(cmd.split())

	def stop(self):
		if self._p:
			self._p.terminate()
			self._p = None

	@property
	def isRunning(self):
		return self._p is not None # FIXME: Check subproc state

class MainWindow(QMainWindow, mainwindow_class):
	def __init__(self, *args):
		super(MainWindow, self).__init__(*args)
		self.setupUi(self)
		self.inst = Xqemu()
		self.settings = SettingsManager()
		self.settings.load()
		self.runButton.setText('Start')

		# Connect signals
		self.runButton.clicked.connect(self.onRunButtonClicked)
		self.actionExit.triggered.connect(self.onExitClicked)
		self.actionSettings.triggered.connect(self.onSettingsClicked)

	def onRunButtonClicked(self):
		if not self.inst.isRunning:
			# No active instance
			try:
				self.inst.start(self.settings)
				self.runButton.setText('Stop')
			except Exception as e:
				QMessageBox.critical(self, 'Error!', str(e))
		else:
			# Instance exists
			self.inst.stop()
			self.runButton.setText('Start')

	def onSettingsClicked(self):
		s = SettingsWindow(self.settings)
		s.exec_()
		self.settings.save()

	def onExitClicked(self):
		self.inst.stop()
		sys.exit(0)

def main():
	app = QApplication(sys.argv)
	app.setStyle('Fusion')

	# Dark theme via https://gist.github.com/gph03n1x/7281135 with modifications
	palette = QtGui.QPalette()
	palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53,53,53))
	palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Base, QtGui.QColor(15,15,15))
	palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53,53,53))
	palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53,53,53))
	palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
	palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(45,197,45).lighter())
	palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
	app.setPalette(palette)

	widget = MainWindow()
	widget.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()