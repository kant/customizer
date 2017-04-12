#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is a python script intended to be used within QGIS to customize the QGEP project
# This file should not be edited, it is configured by sed commands from customize.sh
# And remaining configuration comes from a YAML file.

##################
# IMPORTS

# additional libs
import psycopg2, psycopg2.extras
import yaml
import os

# QGIS imports
from qgis.PyQt.QtXml import QDomDocument, QDomNode
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsMapLayerRegistry, QgsMapLayer, QgsPoint, QgsLayerTreeGroup, QgsApplication, QgsField
from qgis.gui import QgsExternalResourceWidget
from qgis.utils import iface
import qgis2compat.apicompat

# needed for style imports
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtCore import QFile, QTextStream, QVariant
from qgis.PyQt.QtGui import QApplication

####################
# CONFIG UPDATED FROM customizer.sh
# these 3 lines should be automaticaly updated by customizer.sh by sed commands
original_project = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/customizer/../QGEP/project/qgep_en.qgs'
config_file = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/config.yaml.template'
translation_file = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/customizer/../i18n/translation.yaml'

####################
# READ CONFIGURATION
pg_service = "pg_qgep"
with open(config_file, 'r') as stream:
    config_data = yaml.load(stream)
new_project = config_data['output_project']
style_file = config_data['style_file']
style_layer_ids = ['vw_qgep_reach', 'vw_qgep_wastewater_structure']

#######################
# READ TRANSLATION DATA
with open(translation_file, 'r') as stream:
    tr_data = yaml.load(stream)

#######################
# TRANSLATION METHODS
def get_field_translation(cursor, field):
  cursor.execute("SELECT field_name_fr FROM qgep.is_dictionary_od_field WHERE field_name = '{0}' LIMIT 1".format(field))
  trans = cursor.fetchone()
  if trans is None:
      return None
  else:
      return trans[0].lower()

def get_table_translation(cursor, table):
  cursor.execute("SELECT name_fr FROM qgep.is_dictionary_od_table WHERE tablename LIKE '%{0}' LIMIT 1".format(table))
  trans = cursor.fetchone()
  if trans is None:
      return None
  else:
      return trans[0].lower()

def translate_node(node):
    for child in node.children():
      if type(child) == QgsLayerTreeGroup:
        translate_node(child)
    if type(node) == QgsLayerTreeGroup and node.name() in groups:
      node.setName(groups[node.name()])


#######################
# CUSTOMIZE

# open original QGEP project
QgsProject.instance().read(original_project)
QCoreApplication.processEvents()
QgsProject.instance().setFileName(original_project)

# make copy of the project
QgsProject.instance().write(new_project)
QCoreApplication.processEvents()
QgsProject.instance().setFileName(new_project)

# apply custom style
# layer = QgsMapLayerRegistry.instance().mapLayer('vw_qgep_reach')
# layer.readStyle( node, errorMsg )
# QCoreApplication.processEvents()

# add full_path to od_file
vl = QgsMapLayerRegistry.instance().mapLayer("od_file20160921105557083")
vl.addExpressionField( " \"path_relative\" || '\\\\'|| \"identifier\"", QgsField( "full_path", QVariant.String, 'String', -1, -1))
idx = vl.fieldNameIndex("full_path")
vl.editFormConfig().setWidgetType(idx, "ExternalResource")
vl.editFormConfig().setWidgetConfig(idx, { 'UseLink': '1', 'DocumentViewer': QgsExternalResourceWidget.Image})

# pdf link for maintenance events
vl = QgsMapLayerRegistry.instance().mapLayer("vw_qgep_maintenance")
idx = vl.fieldNameIndex("base_data")
vl.editFormConfig().setWidgetType(idx, "ExternalResource")
vl.editFormConfig().setWidgetConfig(idx, { 'UseLink': '1', 'DocumentViewer': QgsExternalResourceWidget.NoContent})

# connect to db
conn = psycopg2.connect("service={0}".format(pg_service))
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# remove raster layers
for layer in QgsMapLayerRegistry.instance().mapLayers().values():
  if layer.type() != QgsMapLayer.VectorLayer:
    QgsMapLayerRegistry.instance().removeMapLayer(layer)

iface.mapCanvas().setCrsTransformEnabled(True) # todo QGIS3
iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem(2056)) # TODO QGIS3 use QgsProject.instance().setCrs instead
QCoreApplication.processEvents()

# set SRID to 2056
for layer in QgsMapLayerRegistry.instance().mapLayers().values():
  if layer.hasGeometryType():
    layer.setCrs(QgsCoordinateReferenceSystem(2056))
    source = layer.source().replace('21781','2056')
    document = QDomDocument("style")
    map_layers_element = document.createElement("maplayers")
    map_layer_element = document.createElement("maplayer")
    layer.writeLayerXml(map_layer_element, document)
    # modify DOM element with new layer reference
    map_layer_element.firstChildElement("datasource").firstChild().setNodeValue(source)
    map_layers_element.appendChild(map_layer_element)
    document.appendChild(map_layers_element)
    # reload layer definition
    layer.readLayerXml(map_layer_element)
    layer.reload()

# translation
for layer in QgsMapLayerRegistry.instance().mapLayers().values():
  if layer.id() in layers.keys():
    layer.setName(layers[layer.id()]['name'])
    # tabs
    if layers[layer.id()].has_key('tabs'):
        for tab in layer.editFormConfig().tabs():
          if tab.name() in layers[layer.id()]['tabs']:
            tab.setName(layers[layer.id()]['tabs'][tab.name()])
          else:
            print("Tab {0} not translated".format(tab.name()))
    # fields
    for idx,field in enumerate(layer.fields()):
      #print(layer.name(),idx,field.name())
      # translation
      trans = get_field_translation(cur, field.name())
      if layers[layer.id()].has_key('additional_translations') and field.name() in layers[layer.id()]['additional_translations']:
        layer.addAttributeAlias(idx, layers[layer.id()]['additional_translations'][field.name()])
      elif trans is not None:
        layer.addAttributeAlias(idx, trans)
      else:
        print("Field {0} is not translated".format(field.name()))
      # update value relation value
      if layer.editFormConfig().widgetType(idx) == 'ValueRelation':
        cfg = layer.editFormConfig().widgetConfig(idx)
        if cfg["Value"] == "value_en":
          cfg["Value"] = "value_fr"
          layer.editFormConfig().setWidgetConfig(idx, cfg)
      # value maps
      if layer.editFormConfig().widgetType(idx) == 'ValueMap':
        cfg = layer.editFormConfig().widgetConfig(idx)
        for key in cfg.keys():
          trans = get_table_translation(cur, cfg[key])
          if trans:
            cfg[trans] = cfg[key]
            del cfg[key]
        layer.editFormConfig().setWidgetConfig(idx, cfg)

# update styles from other project
errMsg = ''
file = QFile(style_file)
file.open(QFile.ReadOnly | QFile.Text)
doc = QDomDocument()
doc.setContent(file)
root = doc.elementsByTagName('qgis.custom.style')
nodes = root.at(0).childNodes()
for i in range(0,nodes.count()):
  elem = nodes.at(i).toElement()
  if elem.tagName() != 'layer' or not elem.hasAttribute('id'):
      continue
  layer_id = elem.attribute('id')
  if layer_id not in style_layer_ids:
      print 'skipping ', layer_id
  layer = QgsMapLayerRegistry.instance().mapLayer(layer_id)
  if not layer:
      print 'layer not found', layer_id
      continue
  print 'loading', layer_id
  style = elem.firstChild()
  style.removeChild(style.firstChildElement('edittypes'))
  layer.readStyle(style, errMsg)

# quickfinder settings
QgsProject.instance().writeEntryBool('quickfinder_plugin', 'project', True)
QgsProject.instance().writeEntry('quickfinder_plugin', 'qftsfilepath', './qgep_sige.qfts')

# remove empty group
tree_root = QgsProject.instance().layerTreeRoot()
grp = tree_root.findGroup('Cadastral Data')
if grp:
  tree_root.removeChildNode(grp)

# translate groups
translate_node(QgsProject.instance().layerTreeRoot())

# background layers
newGroup = QgsProject.instance().createEmbeddedGroup( "Fonds de plans", "/home/drouzaud/Documents/QGEP/sige/cadastre/cadastre_pg.qgs", [] )
if newGroup:
  QgsProject.instance().layerTreeRoot().addChildNode( newGroup )

# disable otf
#iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem(2056))
#QCoreApplication.processEvents()
#iface.mapCanvas().setCrsTransformEnabled(False) # todo QGIS3
#QCoreApplication.processEvents()

# set center
#iface.mapCanvas().setCenter(QgsPoint(6.9072,46.4380))
iface.mapCanvas().setCenter(QgsPoint(2559858,1144177))

# save project
QgsProject.instance().write(new_project)

# exit
QgsApplication.exitQgis()
