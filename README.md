# JacqQVis
A QGIS plugin that renders output from pyJacqQ.

[pyJacqQ](https://github.com/sjirjies/pyJacqQ) detects space-time clusters in case-control studies. Results from pyJacqQ can be imported as layers from CSVs into QGIS. This plugin allows visualizing the resulting clusters through time.

## Dependencies
This plugin requires QGIS 2.0 or greater.

## Installation
1. Clone the repository into [home-folder]/.qgis2/python/plugins.

2. Launch QGIS.

3. Select Plugins | Manage and Install Plugins | All. Check the box besides JacqQVis.

## Loading the Layers
The visualization requires three of the statistical result files from pyJacqQ: global stats, local stats, and date stats. Optionally, JacqQVis can also visualize the focus-local stats.

1. Load the global and date layers into QGIS. This can be done via Layer | Add Layer | Add Delimited Text Layer. Select "No geometry (attribute only table)" as these do not contain point data.

2. Load the local and focus-local layers through Layer | Add Layer | Add Delimited Text Layer. These layers have point data, so you will need to select a coordinate reference system.

3. Open any additional layers such as territorial boundaries.

4. Ensure that each type of statistical layer is present only once under the Layers panel.

## Visualizing Clusters
Launch the plugin by selecting ![Icon](icon_small.png?raw=true "JacqQVis Icon.") from the plugins menu bar or selecting Plugins | Jacquez's Q Visualization | Visualize space-time clusters. It will scan through your open layers and detect the required statistical layers. You will receive an error if you are missing a required layer or if it detects multiple layers of the same statistical type. The following screenshot displays the dialog with simulated cluster data:

![Dialog Visualization](screenshot.png?raw=true "JacqQVis date selection dialog.")

Simply use the date slider or calendar to select a date to view. The dialog can be left open during exploration to view different dates. Local points are displayed as circles and focus-local points as diamonds. QGIS's query tool can be used on the points within the current date to obtain their statistical data. Closing the date selection dialog will exit the plugin.

## Copyright and License
Copyright Saman Jirjies, 2015. This work is available under the GPLv3. Please 
read LICENSE for more info.
