# -*- coding: utf-8 -*-
"""
/***************************************************************************
 JacqQVis
                                 A QGIS plugin
 Visualize Q-stats space-time clusters.
                             -------------------
        begin                : 2015-07-27
        copyright            : (C) 2015 by Saman Jirjies
        email                : saman.jirjies@asu.edu
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load JacqQVis class from file JacqQVis.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .jacqqvis import JacqQVis
    return JacqQVis(iface)
