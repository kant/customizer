from qgis.core import QgsProject
from qgis.utils import iface
import qgis2compat.apicompat

from qgis.PyQt.QtXml import QDomNode, QDomDocument
from qgis.PyQt.QtCore import QFile, QTextStream
from qgis.PyQt.QtGui import QApplication, QClipboard

actions = []
style_file = ''

def openProject():
    actions.append(iface.projectMenu().addAction(u"Sauver la symbologie pour QGEP"))
    actions[0].triggered.connect(copy_style)

def saveProject():
    pass

def closeProject():
    iface.projectMenu().removeAction(actions[0])

def copy_style():
    layer_ids = ['vw_qgep_reach', 'vw_qgep_wastewater_structure']

    doc = QDomDocument('qgis.custom.style')
    root_node = doc.createElement('qgis.custom.style')
    doc.appendChild(root_node)

    for layer_id in layer_ids:
        layer = QgsProject.instance().mapLayer(layer_id)

        layer_node = doc.createElement('layer')
        layer_node.setAttribute('id', layer.id())
        root_node.appendChild(layer_node)
        style_node = doc.createElement('style')
        errorMsg = ""
        print layer.writeStyle( style_node, doc, errorMsg )
        style_node.removeChild(style_node.firstChildElement('edittypes'))
        layer_node.appendChild(style_node)

    out_file = QFile( style_file )
    if out_file.open(QFile.WriteOnly):
      stream = QTextStream( out_file )
      stream << doc.toString()
      out_file.close()
      print('style file written to {0}'.format(style_file))
    else:
      print('error: could not write style file {0}'.format(style_file))
