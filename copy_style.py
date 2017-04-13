style_file = "styles/qgep.style"
layer_ids = ['vw_qgep_reach', 'vw_qgep_wastewater_structure']

from qgis.PyQt.QtXml import QDomNode, QDomDocument
from qgis.PyQt.QtCore import QFile, QTextStream
from qgis.PyQt.QtGui import QApplication, QClipboard

doc = QDomDocument('qgis.custom.style')
root_node = doc.createElement('qgis.custom.style')
doc.appendChild(root_node)

for layer_id in layer_ids:
    layer = QgsMapLayerRegistry.instance().mapLayer(layer_id)

    layer_node = doc.createElement('layer')
    layer_node.setAttribute('id', layer.id())
    root_node.appendChild(layer_node)
    style_node = doc.createElement('style')
    errorMsg = ""
    print layer.writeStyle( style_node, doc, errorMsg )
    style_node.removeChild(style_node.firstChildElement('edittypes'))
    layer_node.appendChild(style_node)


path = QgsProject.instance().homePath() + '/' + style_file
out_file = QFile( path )
if out_file.open(QFile.WriteOnly):
  stream = QTextStream( out_file )
  stream << doc.toString()
  out_file.close()
else:
  print 'error'
  