# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JacqQVis
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

from PyQt4.QtGui import QAction, QIcon, QColor
from PyQt4.QtCore import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from jacqqvis_dialog import JacqQVisDialog
import os.path

from qgis.core import *
from qgis.gui import *

from collections import OrderedDict
import bisect


class JacqQVis:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'JacqQVis_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = JacqQVisDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u"&Jacquez's Q Visualization")
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'JacqQVis')
        self.toolbar.setObjectName(u'JacqQVis')

        # Object attributes for space-time clustering
        self.app_layers = self.AppLayers(None, None, None, None)
        self.time_slices = OrderedDict()
        self.time_slice_date_indexes = {}
        self.number_neighbors = None
        self.dlg.set_date_selection_enable_status(False)
        self.popup = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('JacqQVis', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/JacqQVis/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Visualize space-time clusters'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u"&Jacquez's Q Visualization"),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog if all the proper data layers are available
        has_required_schemas = self.scan_for_layer_schemas()
        if has_required_schemas:
            self.dlg.set_status_message("Scanning/Loading Data From Layers ...")
            self.initializeAllLayers(self.app_layers)
            # Run the dialog event loop
            self.dlg.DateSlider.valueChanged[int].connect(self.new_date_slider_position)
            self.dlg.DateSelector.dateChanged.connect(self.new_date_calendar_selection)
            self.dlg.append_status_message("Ready For Data Browsing.")
            self.dlg.show()
            result = self.dlg.exec_()

    class AppLayers:
        def __init__(self, local_layer, global_layer, date_layer, focus_local_layer):
            self.localLayer = local_layer
            self.globalLayer = global_layer
            self.dateLayer = date_layer
            self.focusLocalLayer = focus_local_layer

    def scan_for_layer_schemas(self):
        layers = self.iface.legendInterface().layers()
        local_layer = None
        date_layer = None
        global_layer = None
        focus_local_layer = None
        multiple_title = "Cannot Resolve Layer Schemas"
        multiple_body = " Detected multiple %s layers. Please remove all expect one and try again."
        for layer in layers:
            all_fields = layer.pendingFields()
            for field in all_fields:
                if field.name().lower() == "qit_days":
                    if local_layer:
                        self.prompt_error(multiple_title, multiple_body % "local Qit")
                        return False
                    local_layer = layer
                elif field.name().lower() == "qt_cases":
                    if date_layer:
                        self.prompt_error(multiple_title, multiple_body % "date Qt")
                        return False
                    date_layer = layer
                elif field.name().lower() == "q_case_years":
                    if global_layer:
                        self.prompt_error(multiple_title, multiple_body % "global Q")
                        return False
                    global_layer = layer
                elif field.name().lower() == "qift_days":
                    if focus_local_layer:
                        self.prompt_error(multiple_title, multiple_body % "focus Qift")
                        return False
                    focus_local_layer = layer
        missing_title = "Missing %s Layer"
        missing_body = "Could not find %s layer. Did you forget to load it?"
        if not local_layer:
            self.prompt_error(missing_title % "Qit", missing_body % "Qit local")
            return False
        if not date_layer:
            self.prompt_error(missing_title % "Qt", missing_body % "Qt date")
            return False
        if not global_layer:
            self.prompt_error(missing_title % "Q", missing_body % "Q global")
            return False
        if not focus_local_layer:
            self.dlg.set_status_message("No Qift layer provided; cannot render focus points.")
        self.app_layers = self.AppLayers(local_layer, global_layer, date_layer, focus_local_layer)
        return True

    def initializeAllLayers(self, app_layers):
        # Local layer must be created before focus and date layer for extraction of dates
        self.load_global_stats_from_layer(app_layers.globalLayer)
        self.create_local_time_slice_layer(app_layers.localLayer)
        if app_layers.focusLocalLayer:
            self.create_focus_local_time_slice_layer(app_layers.focusLocalLayer)
        self.load_date_stats_from_layer(app_layers.dateLayer)

    def prompt_error(self, title, message):
        self.dlg.show_error(title, message)

    def create_local_time_slice_layer(self, input_layer):
        # Hide the reference layer
        self.iface.legendInterface().setLayerVisible(input_layer, False)

        # Find the minimum date
        unique_start_dates = self.get_unique_dates(input_layer, 'start_date')
        first_start_date = min(unique_start_dates)
        last_start_date = max(unique_start_dates)

        # Categorize the attributes according to date
        sorted_unique_dates = sorted(list(unique_start_dates))
        self.time_slices = OrderedDict()
        self.time_slice_date_indexes = {}
        # Map dates to TimeSliceData objects and dates to indexes
        for index, x_date in enumerate(sorted_unique_dates):
            self.time_slices[int(x_date)] = TimeSliceData(x_date)
            # Index is needed for setting the date slider to the proper position
            self.time_slice_date_indexes[x_date] = index
        # Sort features into their respective time slice objects
        for feature in input_layer.getFeatures():
            self.time_slices[feature['start_date']].local_point_features.append(feature)
        # Convert features into point features
        for time_slice_object in self.time_slices.values():
            item = time_slice_object
            item.local_point_features = \
                self.convert_features_to_point_features(item.local_point_features,
                                                        ['start_date', 'end_date', 'id', 'x',
                                                         'y', 'Qit_days', 'pval', 'sig'])

        local_time_slice_layer = QgsVectorLayer("Point?crs=epsg:4326", "Local Stats", "memory")
        local_time_slice_layer.startEditing()
        local_provider = local_time_slice_layer.dataProvider()
        local_provider.addAttributes([QgsField("start_date", QVariant.String),
                                      QgsField("end_date", QVariant.Int),
                                      QgsField("id", QVariant.Double),
                                      QgsField("x", QVariant.Double),
                                      QgsField("y", QVariant.Double),
                                      QgsField("Qit_days", QVariant.Int),
                                      QgsField("pval", QVariant.Double),
                                      QgsField("sig", QVariant.Int)])

        color_attribute = 'Qit_days'
        ranges_list = []
        colors = ColorGradient.linear_gradient("#FFFFFF", "#880000", n=self.number_neighbors)['hex']

        # Establish the ranges based on number of neighbors
        for category_number in range(self.number_neighbors):
            symbol = QgsSymbolV2.defaultSymbol(local_time_slice_layer.geometryType())
            symbol.setColor(QColor(colors[category_number]))
            symbol.setAlpha(1)
            lower_number = float(category_number)
            higher_number = lower_number + 1
            color_range = QgsRendererRangeV2(lower_number, higher_number, symbol,
                                             "%f - %f" % (lower_number, higher_number))
            ranges_list.append(color_range)

        local_renderer = QgsGraduatedSymbolRendererV2('', ranges_list)
        local_renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
        # myRenderer.setSourceColorRamp(ramp)
        local_renderer.setClassAttribute(color_attribute)
        local_time_slice_layer.setRendererV2(local_renderer)

        local_time_slice_layer.updateExtents()
        local_time_slice_layer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(local_time_slice_layer)
        self.app_layers.localLayer = local_time_slice_layer
        self.iface.mapCanvas().refresh()

        # Enable date selection and load the first time slice layers
        self.dlg.set_date_selection_enable_status(True)
        self.dlg.set_max_date_index(len(self.time_slices.keys()) - 1)
        self.dlg.set_calendar_date(str(first_start_date))
        self.dlg.set_calendar_range(first_start_date, last_start_date)
        self.set_layer_time_slice_features(self.app_layers.localLayer,
                                           self.time_slices[int(first_start_date)].local_point_features)

    def create_focus_local_time_slice_layer(self, input_layer):
        self.iface.legendInterface().setLayerVisible(input_layer, False)
        # Sort features into their respective time slice objects
        for feature in input_layer.getFeatures():
            self.time_slices[feature['start_date']].local_focus_point_features.append(feature)
        # Convert features into point features
        for time_slice_object in self.time_slices.values():
            item = time_slice_object
            item.local_focus_point_features = \
                self.convert_features_to_point_features(item.local_focus_point_features,
                                                        ['start_date', 'end_date', 'id', 'x', 'y',
                                                         'Qift_days', 'pval', 'sig'])
        local_focus_time_slice_layer = QgsVectorLayer("Point?crs=epsg:4326", "Focus Local Stats", "memory")
        local_focus_time_slice_layer.startEditing()
        local_provider = local_focus_time_slice_layer.dataProvider()
        local_provider.addAttributes([QgsField("start_date", QVariant.String), QgsField("end_date", QVariant.Int),
                                      QgsField("id", QVariant.Double), QgsField("x", QVariant.Double),
                                      QgsField("y", QVariant.Double), QgsField("Qift_days", QVariant.Int),
                                      QgsField("pval", QVariant.Double), QgsField("sig", QVariant.Int)])

        color_attribute = 'Qift_days'
        ranges_list = []
        colors = ColorGradient.linear_gradient("#FFFFFF", "#000000", n=self.number_neighbors)['hex']

        # Establish the ranges based on number of neighbors
        for category_number in range(self.number_neighbors):
            # Set the focus local points to a different symbol style
            symbol = QgsMarkerSymbolV2.createSimple({'name': 'diamond', 'size': '4', 'outline_color': '0,125,0,255',
                                                     'outline_style': 'solid', 'outline_width': '0.40'})
            symbol.setColor(QColor(colors[category_number]))
            symbol.setAlpha(1)
            lower_number = float(category_number)
            higher_number = lower_number + 1
            color_range = QgsRendererRangeV2(lower_number, higher_number, symbol,
                                             "%f - %f" % (lower_number, higher_number))
            ranges_list.append(color_range)

        focus_renderer = QgsGraduatedSymbolRendererV2('', ranges_list)
        focus_renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
        # myRenderer.setSourceColorRamp(ramp)
        focus_renderer.setClassAttribute(color_attribute)
        local_focus_time_slice_layer.setRendererV2(focus_renderer)

        symbolList = local_focus_time_slice_layer.rendererV2().symbols()

        local_focus_time_slice_layer.updateExtents()
        local_focus_time_slice_layer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(local_focus_time_slice_layer)
        self.app_layers.focusLocalLayer = local_focus_time_slice_layer
        self.iface.mapCanvas().refresh()

    def load_global_stats_from_layer(self, input_layer):
        field_names = []
        field_values = []
        fields = input_layer.pendingFields()
        for field in fields:
            field_names.append(field.name())
        for feature in input_layer.getFeatures():
            for metric in feature:
                field_values.append(metric)
        data = OrderedDict(zip(field_names, field_values))
        self.number_neighbors = int(data['k'])
        self.dlg.set_global_table_data(data)

    def load_date_stats_from_layer(self, input_layer):
        # Hide the reference layer
        self.iface.legendInterface().setLayerVisible(input_layer, False)
        # Sort features into their respective time slice objects
        for feature in input_layer.getFeatures():
            start_date = feature['start_date']
            # end_date = feature['end_date']
            Qt_cases = feature['Qt_cases']
            pval = feature['pval']
            sig = feature['sig']
            time_slice_object = self.time_slices[start_date]
            time_slice_object.Qt_statistic = (Qt_cases, pval, sig)

    def update_everything_by_date(self, date):
        self.set_layer_time_slice_features(self.app_layers.localLayer, self.time_slices[date].local_point_features)
        if self.app_layers.focusLocalLayer:
            self.set_layer_time_slice_features(self.app_layers.focusLocalLayer,
                                               self.time_slices[date].local_focus_point_features)
        self.update_date_statistics(date)

    def update_date_statistics(self, selected_date):
        stat = self.time_slices[selected_date].Qt_statistic
        if stat:
            self.dlg.set_date_stat_value("%s case-days, p-value %s, significant? %s" %
                                         (str(stat[0]), str(stat[1]), str(stat[2])))
        else:
            self.dlg.set_date_stat_value("")

    def new_date_calendar_selection(self):
        date = int(self.dlg.get_calendar_date_selection())
        first_date = self.time_slices.keys()[0]
        if date < first_date:
            date = first_date
        if date not in self.time_slices:
            span_starter = self.get_largest_of_all_lower(list(self.time_slices.keys()), date)
            self.dlg.set_calendar_date(span_starter)
            self.dlg.set_status_message("%d encompasses %d. Rolled back to %d." % (span_starter, date, span_starter))
        else:
            self.dlg.set_status_message("")
            self.dlg.set_slider_position(int(self.time_slice_date_indexes[date]))
            self.update_everything_by_date(date)

    def new_date_slider_position(self):
        date = self.time_slices.keys()[int(self.dlg.get_selected_date())]
        self.dlg.set_calendar_date(str(date))
        self.update_everything_by_date(int(date))

    def convert_features_to_point_features(self, data, schema):
        features = []
        for datum in data:
            point = QgsPoint(datum['x'], datum['y'])
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPoint(point))
            attributes = []
            for attr in schema:
                attributes.append(datum[attr])
            feature.setAttributes(attributes)
            features.append(datum)
        return features

    def set_layer_time_slice_features(self, layer, features_add):
        layer.startEditing()
        layer.updateFields()
        provider = layer.dataProvider()
        provider.deleteFeatures([feature.id() for feature in layer.getFeatures()])
        provider.addFeatures(features_add)
        layer.updateExtents()
        layer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        self.iface.legendInterface().refreshLayerSymbology(layer)
        self.redraw_layer(layer)
        self.iface.mapCanvas().refresh()

    def where(self, layer, exp):
        exp = QgsExpression(exp)
        if exp.hasParserError():
            raise Exception(exp.parserErrorString())
        exp.prepare(layer.pendingFields())
        for feature in layer.getFeatures():
            value = exp.evaluate(feature)
            if exp.hasEvalError():
                raise ValueError(exp.evalErrorString())
            if bool(value):
                yield feature

    def get_unique_dates(self, layer, date_string):
        unique_dates = set()
        for feature in self.where(layer, date_string + ' IS NOT NULL'):
            unique_dates.add(feature[date_string])
        return unique_dates

    def get_selected_layer(self):
        return self.iface.activeLayer()

    def redraw_layer(self, layer):
        if self.iface.mapCanvas().isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.iface.mapCanvas().refresh()

    @staticmethod
    def get_largest_of_all_lower(array, value):
        if len(array) == 1:
            return array[0]
        index = bisect.bisect(array, value)
        return array[index-1]


class TimeSliceData:
    def __init__(self, start_date):
        self.start_date = start_date
        self.local_point_features = []
        self.local_focus_point_features = []
        self.Qt_statistic = None


class ColorGradient:
    # Methods in this class taken from http://bsou.io/posts/color-gradients-with-python

    @staticmethod
    def color_dict(gradient):
        """ Takes in a list of RGB sub-lists and returns dictionary of
        colors in RGB and hex form for use in a graphing function
        defined later on """
        return {"hex": [ColorGradient.rgb_to_hex(RGB) for RGB in gradient],
                "r": [RGB[0] for RGB in gradient],
                "g": [RGB[1] for RGB in gradient],
                "b": [RGB[2] for RGB in gradient]}

    @staticmethod
    def linear_gradient(start_hex, finish_hex="#FFFFFF", n=10):
        """ returns a gradient list of (n) colors between
        two hex colors. start_hex and finish_hex
        should be the full six-digit color string,
        including the number sign ("#FFFFFF") """
        # Starting and ending colors in RGB form
        s = ColorGradient.hex_to_rgb(start_hex)
        f = ColorGradient.hex_to_rgb(finish_hex)
        # Initialize a list of the output colors with the starting color
        rgb_list = [s]
        # Calculate a color at each evenly spaced value of t from 1 to n
        for t in range(1, n):
            # Interpolate RGB vector for color at the current value of t
            curr_vector = [int(s[j] + (float(t) / (n - 1)) * (f[j] - s[j])) for j in range(3)]
            # Add it to our list of output colors
            rgb_list.append(curr_vector)
        return ColorGradient.color_dict(rgb_list)

    @staticmethod
    def hex_to_rgb(hex):
        """ "#FFFFFF" -> [255,255,255] """
        # Pass 16 to the integer function for change of base
        return [int(hex[i:i + 2], 16) for i in range(1, 6, 2)]

    @staticmethod
    def rgb_to_hex(rgb):
        """ [255,255,255] -> "#FFFFFF" """
        # Components need to be integers for hex to make sense
        rgb = [int(x) for x in rgb]
        return "#" + "".join(["0{0:x}".format(v) if v < 16 else
                              "{0:x}".format(v) for v in rgb])
