#from msilib.schema import PublishComponent

from PyQt5.QtCore import QIODevice, QTimer, QSettings
#from pyqtgraph.examples.MultiDataPlot import widget
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import rabbitpy
from rabbitpy import publish

from design import Ui_Form

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg

class MainForm(qtw.QWidget, Ui_Form):

    global serial, portlist
    global rxstring, rssi, dataConfig

    startedConsumer = qtc.pyqtSignal(str)
    toPublish = qtc.pyqtSignal(str, str)

    def __init__(self, *args, **kwargs):
        global serial, portlist, rxstring

        super().__init__(*args, **kwargs)

        self.setupUi(self)

        self.settings = QSettings('RER', 'mvr')
        self.loadSetting()

        self.UpdateListComPort.clicked.connect(self.UpdateComport)
        self.openButton.clicked.connect(self.open_port)
        self.rabbitButton.clicked.connect(self.startConcumer)
        self.pushButton.clicked.connect(self.publish)

        serial = QSerialPort()
        serial.readyRead.connect(self.on_ready_read)

        rxstring = ''
        rssi = ''
        self.UpdateComport()

        timer = QTimer(self)
        timer.timeout.connect(self.updateData)
        timer.start(3000)

        self.startConcumer()

    def saveSetting(self):
        self.settings.setValue('userNameEdit', self.userNameEdit.displayText())
        self.settings.setValue('userPasswordEdit', self.userPasswordEdit.displayText())
        self.settings.setValue('hostEdit', self.hostEdit.displayText())
        self.settings.setValue('portEdit', self.portEdit.displayText())
        self.settings.setValue('virtualHostEdit', self.virtualHostEdit.displayText())
        self.settings.setValue('queueEdit', self.queueEdit.displayText())

    def loadSetting(self):
        self.userNameEdit.setText(self.settings.value("userNameEdit", 'valkiria_user'))
        self.userPasswordEdit.setText(self.settings.value("userPasswordEdit", '314159265'))
        self.hostEdit.setText(self.settings.value("hostEdit", 'mizar.kyiv.ua'))
        self.portEdit.setText(self.settings.value("portEdit", '5672'))
        self.virtualHostEdit.setText(self.settings.value("virtualHostEdit", 'valkiria'))
        self.queueEdit.setText(self.settings.value("queueEdit", '464'))

    def closeEvent(self, a0):
        self.saveSetting()

    def UpdateComport(self):
        global portlist
        portlist = []
        portlist.clear()
        self.comPortComboBox.clear()

        ports = QSerialPortInfo().availablePorts()
        for port in ports:
            portlist.append(port.portName())
        self.comPortComboBox.addItems(portlist)

    def open_port(self):
        port_name = self.comPortComboBox.currentText()
        if serial.isOpen():
            serial.close()
        serial.setPortName(port_name)
        serial.setBaudRate(QSerialPort.BaudRate.Baud9600)
        serial.setDataBits(QSerialPort.DataBits.Data8)
        serial.setParity(QSerialPort.Parity.NoParity)
        serial.setStopBits(QSerialPort.StopBits.OneStop)
        serial.open(QIODevice.ReadWrite)

    def on_ready_read(self):
        global rxstring, rssi, dataConfig
        indexFirst = -1
        rx = serial.readLine()
        try:
            rxs = str(rx, 'utf-8')
        except:
            indexFirst = -1
            rxs = ''
            rxstring = ''
            #print('rx is uncorrect ')
        rxstring += rxs
        indexFirst = rxstring.find('#')

        if indexFirst == -1:
            rxstring = ''
        else:
            indexLast = rxstring.find('\r')
            if indexLast != -1:
                rxstring = rxstring[indexFirst+6:indexLast]
                rssi = rxstring
                rxstring = ''

        #print("rssi " + rssi)
        self.lcdRSSI.display(rssi)
        self.toPublish.emit(self.queueEdit.displayText(), rssi)

    def write_data(self, data):
        if serial.isOpen():
            txs = ','.join(map(str, data)) + '\n'
            serial.write(txs.encode()) #txs.encode()
            print(data)

    def updateData(self):
        if self.lcdFrequency.value() != 0:
            data = '#SET ' + str(int(self.lcdFrequency.value()))
            self.write_data(data)

    def startConcumer(self):
        self.concumer = Consumer()
        self.concumer_thread = qtc.QThread()

        # Assign the worker to the thread and start the thread
        self.concumer.moveToThread(self.concumer_thread)
        self.concumer_thread.start()

        self.concumer.received.connect(self.updateFrequency)
        self.startedConsumer.connect(self.concumer.startConsumer)

        self.startedConsumer.emit(self.queueEdit.displayText())

        self.publisher = Publisher()
        self.publisher_thread = qtc.QThread()

        # Assign the worker to the thread and start the thread
        self.publisher.moveToThread(self.publisher_thread)
        self.publisher_thread.start()

        #self.publisher.sent.connect(self.)
        self.toPublish.connect(self.publisher.publish)

    @qtc.pyqtSlot(str)
    def updateFrequency(self, frequency):
        self.lcdFrequency.display(frequency)

    def publish(self):
        global rssi

        self.toPublish.emit(self.queueEdit.displayText(), rssi)

class Consumer(qtc.QObject):

    received = qtc.pyqtSignal(str)

    @qtc.pyqtSlot(str)
    def startConsumer(self, queue):
        with rabbitpy.Connection('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria') as conn:
            with conn.channel() as channel:
                queue = rabbitpy.Queue(channel, 'frequency' + queue)

                # Exit on CTRL-C
                try:
                    # Consume the message
                    for message in queue:
                        frequency = message.body.decode("utf-8")
                        message.ack()
                        self.received.emit(frequency)
                except KeyboardInterrupt:
                    print('Exited consumer')

class Publisher(qtc.QObject):

    sent = qtc.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.conn = rabbitpy.Connection('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria')
        self.channel = self.conn.channel()
        #queue = rabbitpy.Queue(self.channel, 'RSSI' + queue)


    @qtc.pyqtSlot(str, str)
    def publish(self, queue, rssi):
       # with rabbitpy.Connection('amqp://valkiria_user:314159265@mizar.kyiv.ua:5672/valkiria') as conn:
            #with conn.channel() as channel:
                #queue = rabbitpy.Queue(channel, 'RSSI' + queue)
        EXCHANGE = 'RSSI' + queue
        ROUTING_KEY = ''

        # Exit on CTRL-C
        try:
            message = rabbitpy.Message(self.channel, rssi)
            message.publish(EXCHANGE, ROUTING_KEY)
            self.sent.emit()
        except KeyboardInterrupt:
            print('Exited consumer')

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app = qtw.QApplication([])
    widget = MainForm()
    widget.show()

    app.exec_()