# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JacqQVisDialog
                                 A QGIS plugin
 Visualize Q-stats space-time clusters.
                             -------------------
        begin                : 2015-07-27
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Saman Jirjies
        email                : saman.jirjies@asu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'jacqqvis_dialog_base.ui'))


class JacqQVisDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(JacqQVisDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def set_date_selection_enable_status(self, status):
        self.DateSlider.setEnabled(status)
        self.DateSelector.setEnabled(status)

    def set_max_date_index(self, number):
        self.DateSlider.setRange(0, number)

    def get_selected_date(self):
        return self.DateSlider.value()

    def get_calendar_date_selection(self):
        return self.DateSelector.date().toString('yyyyMMdd')

    def set_calendar_range(self, lowest_date, highest_date):
        lowest = QDate().fromString(str(lowest_date), "yyyyMMdd")
        highest = QDate().fromString(str(highest_date), "yyyyMMdd")
        self.DateSelector.setDateRange(lowest, highest)

    def set_calendar_date(self, date):
        self.DateSelector.setDate(QDate().fromString(str(date), "yyyyMMdd"))

    def set_slider_position(self, position_index):
        self.DateSlider.setValue(position_index)

    def set_status_message(self, message):
        self.StatusMessage.setText("-> " + message)

    def append_status_message(self, message):
        prior = self.StatusMessage.text()
        print(prior)
        if prior != "" and prior != "-> ":
            self.StatusMessage.setText(prior + " " + message)
        else:
            self.set_status_message(message)

    def set_date_stat_value(self, string):
        self.ValueDateStat.setText(string)

    def set_global_table_data(self, data_dict):
        self.GlobalResultsTable.setRowCount(1)
        self.GlobalResultsTable.setColumnCount(len(data_dict.keys()))
        self.GlobalResultsTable.setHorizontalHeaderLabels(data_dict.keys())
        self.GlobalResultsTable.setVerticalHeaderLabels([""])
        for index, value in enumerate(data_dict.values()):
            self.GlobalResultsTable.setItem(0, index, QtGui.QTableWidgetItem(str(value)))
        self.GlobalResultsTable.resizeColumnsToContents()

    def show_error(self, title, message):
        QtGui.QMessageBox.warning(self, title, message)
