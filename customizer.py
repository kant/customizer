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

# QGIS imports
from qgis.PyQt.QtXml import QDomDocument, QDomNode
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsMapLayer, QgsPoint, \
    QgsLayerTreeGroup, QgsApplication, QgsField
from qgis.gui import QgsExternalResourceWidget
from qgis.utils import iface
import qgis2compat.apicompat

# needed for style imports
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtCore import QFile, QVariant

##################
# Open python console for debugging
iface.actionShowPythonDialog().trigger()

####################
# CONFIG UPDATED FROM customizer.sh
# these 3 lines should be automaticaly updated by customizer.sh by sed commands
original_project = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/QGEP/project/qgep_en.qgs'
config_file = '/home/drouzaud/Documents/QGEP/sige/sige-config.yaml'
translation_file = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/i18n/fr.yaml'

####################
# READ CONFIGURATION
pg_service = "pg_qgep"
with open(config_file, 'r') as stream:
    config_data = yaml.load(stream)
new_project = config_data['output_project']

style_layer_ids = ['vw_qgep_reach', 'vw_qgep_wastewater_structure']

#######################
# READ TRANSLATION DATA
with open(translation_file, 'r') as stream:
    tr_data = yaml.load(stream)


#######################
# TRANSLATION METHODS
def get_field_translation(cursor, field):
    cursor.execute(
        "SELECT field_name_fr FROM qgep.is_dictionary_od_field WHERE field_name = '{0}' LIMIT 1".format(field))
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
    if type(node) == QgsLayerTreeGroup and node.name() in tr_data['groups']:
        node.setName(tr_data['groups'][node.name()])


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

# add full_path to od_file
vl = QgsProject.instance().mapLayer("od_file20160921105557083")
vl.addExpressionField(" \"path_relative\" || '\\\\'|| \"identifier\"",
                      QgsField("full_path", QVariant.String, 'String', -1, -1))
idx = vl.fieldNameIndex("full_path")
vl.editFormConfig().setWidgetType(idx, "ExternalResource")
vl.editFormConfig().setWidgetConfig(idx, {'UseLink': '1', 'DocumentViewer': QgsExternalResourceWidget.Image})

# pdf link for maintenance events
vl = QgsProject.instance().mapLayer("vw_qgep_maintenance")
idx = vl.fieldNameIndex("base_data")
vl.editFormConfig().setWidgetType(idx, "ExternalResource")
vl.editFormConfig().setWidgetConfig(idx, {'UseLink': '1', 'DocumentViewer': QgsExternalResourceWidget.NoContent})

# connect to db
conn = psycopg2.connect("service={0}".format(pg_service))
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# remove raster layers
for layer in QgsProject.instance().mapLayers().values():
    if layer.type() != QgsMapLayer.VectorLayer:
        QgsProject.instance().removeMapLayer(layer)

iface.mapCanvas().setCrsTransformEnabled(True)  # todo QGIS3
iface.mapCanvas().setDestinationCrs(
    QgsCoordinateReferenceSystem(2056))  # TODO QGIS3 use QgsProject.instance().setCrs instead
QCoreApplication.processEvents()

# set SRID to 2056
if 'srid' in config_data:
    for layer in QgsProject.instance().mapLayers().values():
        if layer.hasGeometryType():
            layer.setCrs(QgsCoordinateReferenceSystem(int(config_data['srid'])))
            source = layer.source().replace('21781', str((config_data['srid'])))
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
for layer in QgsProject.instance().mapLayers().values():
    if layer.id() in tr_data['layers']:
        print('Translating layer: {0}'.format(layer.name()))
        layer.setName(tr_data['layers'][layer.id()]['name'])
        # tabs
        if 'tabs' in tr_data['layers'][layer.id()]:
            for tab in layer.editFormConfig().tabs():
                if tab.name() in tr_data['layers'][layer.id()]['tabs']:
                    tab.setName(tr_data['layers'][layer.id()]['tabs'][tab.name()])
                else:
                    print("Tab {0} not translated".format(tab.name()))
        # fields
        for idx, field in enumerate(layer.fields()):
            # print(layer.name(),idx,field.name())
            # translation
            trans = get_field_translation(cur, field.name())
            if ('additional_translations' in tr_data['layers'][layer.id()]
                    and isinstance(tr_data['layers'][layer.id()]['additional_translations'], list)
                    and field.name() in tr_data['layers'][layer.id()]['additional_translations']):
                layer.addAttributeAlias(idx, tr_data['layers'][layer.id()]['additional_translations'][field.name()])
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
if 'style_file' in config_data:
    errMsg = ''
    file = QFile(config_data['style_file'])
    file.open(QFile.ReadOnly | QFile.Text)
    doc = QDomDocument()
    doc.setContent(file)
    root = doc.elementsByTagName('qgis.custom.style')
    nodes = root.at(0).childNodes()
    for i in range(0, nodes.count()):
        elem = nodes.at(i).toElement()
        if elem.tagName() != 'layer' or not elem.hasAttribute('id'):
            continue
        layer_id = elem.attribute('id')
        if layer_id not in style_layer_ids:
            print('skipping ', layer_id)
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            print('layer not found', layer_id)
            continue
        print('loading', layer_id)
        style = elem.firstChild()
        style.removeChild(style.firstChildElement('edittypes'))
        layer.readStyle(style, errMsg)


# quickfinder settings
if 'quickfinder' in config_data:
    QgsProject.instance().writeEntryBool('quickfinder_plugin', 'project', True)
    QgsProject.instance().writeEntry('quickfinder_plugin', 'qftsfilepath', config_data['quickfinder'])


# remove empty group
tree_root = QgsProject.instance().layerTreeRoot()
grp = tree_root.findGroup('Cadastral Data')
if grp:
    tree_root.removeChildNode(grp)

# translate groups
translate_node(QgsProject.instance().layerTreeRoot())

# background layers
if 'background_layers' in config_data:
    for bgl in config_data['background_layers']:
        print('background layer: {0}: {1}'.format(bgl['group'], bgl['file']))
        newGroup = QgsProject.instance().createEmbeddedGroup(bgl['group'], bgl['file'], [])
        if newGroup:
            QgsProject.instance().layerTreeRoot().addChildNode(newGroup)


# set center
if 'map_center' in config_data:
    iface.mapCanvas().setCenter(QgsPoint(config_data['map_center']['x'], config_data['map_center']['y']))

# integrate macros to save symbology
symbology_macro_file = '/home/drouzaud/Documents/QGEP/sige/QGEP-customizer/macros_symbology.py'
with open (symbology_macro_file, "r") as myfile:
    code = myfile.read()
print QgsProject.instance().writeEntry( "Macros", "/pythonCode", code )
QgsProject.instance().setDirty( True )

# save project
#QgsProject.instance().write(new_project)
iface.actionSaveProject().trigger()

# exit
QCoreApplication.processEvents()
QgsApplication.exitQgis()
