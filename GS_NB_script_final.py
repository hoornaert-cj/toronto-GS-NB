import processing, os, requests
from qgis.core import *
from qgis.PyQt import QtGui

#add the Google basemap
service_url = "mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}" 
service_uri = "type=xyz&zmin=0&zmax=21&url=https://"+requests.utils.quote(service_url)
tms_layer = iface.addRasterLayer(service_uri, "Google Road Maps", "wms")

#Reproject the shapefiles in C:/temp from WGS 84 to UTM 17 so that the area units will be 
#in metres, and area can therefore be calculated
#Define the input and output CRS, so that your input layers can be reprojected
input_crs = QgsCoordinateReferenceSystem('EPSG:4326')
output_crs = QgsCoordinateReferenceSystem('EPSG:6660')

# set directory path containing shapefiles
input_dir = "C:/temp"

# iterate through shapefiles in directory
for file_name in os.listdir(input_dir):
    if file_name.endswith(".shp"):
        # load shapefile into QGIS
        layer = QgsVectorLayer(os.path.join(input_dir, file_name), file_name, "ogr")
        print('layer added')
        
        # apply reprojection and save output shapefile
        processing.run("native:reprojectlayer", {
            'INPUT': layer,
            'TARGET_CRS': output_crs,
            'OUTPUT': os.path.join(input_dir, file_name.replace(".shp", "_UTM17.shp"))
        })
        # remove the loaded layer from QGIS
        QgsProject.instance().removeMapLayer(layer)

#set variables for the input (input_fn = green space data, overlay_fn = neighbourhoods)
input_fn = 'C:/temp/Green_Spaces_UTM17.shp'
overlay_fn = 'C:/temp/Neighbourhoods_UTM17.shp'

#calculate the area of the neighbourhood polygons, which will later be used to calculate the
#percentage of green space per neigbhourhood
lyr = QgsVectorLayer(overlay_fn, '', 'ogr')
pv = lyr.dataProvider()
#add a new field called Area_NB, which gives you the area of the neighbourhood in square metres
pv.addAttributes([QgsField('Area_NB', QVariant.Double)])
lyr.updateFields()

#this expression will calculate the area of neighbourhoods in square metres
exp0 = QgsExpression('$area')
context = QgsExpressionContext()
context.appendScopes(\
QgsExpressionContextUtils.globalProjectLayerScopes(lyr))

with edit(lyr):
    for feat in lyr.getFeatures():
        context.setFeature(feat)
        feat['Area_NB'] = exp0.evaluate(context)
        lyr.updateFeature(feat)
print('NB Area calculated')

#Run the intersect tool to see where the green spaces intersect the neighbourhoods. Save the result to a variable called 'intersect_shp'
results = processing.run("saga:intersect",\
{'A': input_fn,\
'B': lyr,\
'SPLIT':True, \
'RESULT': 'TEMPORARY_OUTPUT'}) 
print('Intersect Completed')
intersect_shp = results['RESULT']

#repair any invalid geometry otherwise the dissolve tool will throw an error
results = processing.run("native:fixgeometries",\
{'INPUT':intersect_shp \
,'OUTPUT':'TEMPORARY_OUTPUT'})
fixed_intersect = results['OUTPUT']

#Using the dissolve tool, dissolve the result of the intersect so that you have one green space polygon per neighbourhood
#this will be used to calculate the green space per neighbourhood. The result will be saved to a variable called 'dissolve_shp'\
# to be used by the next processing tool
results = processing.run("native:dissolve", \
{'INPUT':fixed_intersect,\
'FIELD':'AREA_SHORT_1',\
'OUTPUT':'TEMPORARY_OUTPUT'})
print('Dissolve Completed')
dissolve_shp = results['OUTPUT']

#calculate the area of the dissolved polygons, which will give you the green space area for each neighborhood
#lyr = dissolve_shp # QgVectorLayer(dissolve_shp, '', 'ogr')
pv = dissolve_shp.dataProvider()
#add a new field called Area_GS, which gives you the area of the green spaces
pv.addAttributes([QgsField('Area_GS', QVariant.Double)])
dissolve_shp.updateFields()

#this expression will calculate the area of green spaces in square kilometres
expl = QgsExpression('$area')
context = QgsExpressionContext()
context.appendScopes(\
QgsExpressionContextUtils.globalProjectLayerScopes(dissolve_shp))

#for each feature in the dissolved neighbourhood/green spaces layer, calculate the area in square kilometres
with edit(dissolve_shp):
    for feat in dissolve_shp.getFeatures():
        context.setFeature(feat)
        feat['Area_GS'] = expl.evaluate(context)
        dissolve_shp.updateFeature(feat)
print('Area calculated')

#Join the results of the previous layer which shows the green space area for each neighbourhood to the neighbourhoods shapefile
#so that the end results can be visualized for each neighbourhood
results = processing.run("native:joinattributestable",\
{'INPUT': overlay_fn,\
'FIELD': 'AREA_SHORT',\
'INPUT_2':dissolve_shp, \
'FIELD_2': 'AREA_SHORT_1',\
'METHOD':1,\
'PREFIX':'JJ_',\
'OUTPUT':'TEMPORARY_OUTPUT' \
})
print('Join Attributes Completed')
join_shp = results['OUTPUT']

#set the filename variable to be used in the file writer
fn = 'C:/temp/output/Neighbourhoods_GreenSpaces_UTM17.shp'
options = QgsVectorFileWriter.SaveVectorOptions()
options.driverName = "ESRI Shapefile"
QgsVectorFileWriter.writeAsVectorFormatV2(join_shp, fn, QgsCoordinateTransformContext(), options)
#add the joined layer to the project
iface.addVectorLayer(fn, '', 'ogr')

#calculate the area of green space per neighborhood by dividing the area of green space calculated in dissolve_shp (JJ_area_GS) by the area
# of the neighbourhood (AREA field) then multiplying that value by 100 to compute the percentage
lyr = QgsProject.instance().mapLayersByName('Neighbourhoods_GreenSpaces_UTM17')[0]

#calculate the percentage of green space per neighborhood by dividing
#the green space area (dissolve_shp's area) by the total area of the 
#neighbourhood (Area) and multiplying by 100
pv = lyr.dataProvider()
#add a new field called Area_GS, which gives you the area of the green spaces
pv.addAttributes([QgsField('PCT_GS', QVariant.Double)])
lyr.updateFields()

#this expression will calculate the area of green spaces in square kilometres
expl = QgsExpression(('"JJ_Area_GS"/"Area_NB"' + '*100'))
context = QgsExpressionContext()
context.appendScopes(\
QgsExpressionContextUtils.globalProjectLayerScopes(lyr))

#for each feature in the dissolved neighbourhood/green spaces layer, calculate the area in square kilometres
with edit(lyr):
    for feat in lyr.getFeatures():
        context.setFeature(feat)
        feat['PCT_GS'] = expl.evaluate(context)
        lyr.updateFeature(feat)
print('Area calculated')

#symbolize the layer using graduated symbology
#lyr = QgsProject.instance().mapLayersByName('Neighbourhoods_GreenSpaces_UTM17')[0]
#symbolize this new layer and add it to the project
field_name = 'PCT_GS'
rangeList = []
breaks = [0, 5, 10, 20, 30, 40, 50, 60, 70]
color_sym = ['#00eb00', '#00b100', '#009d00', '#008900', '#007600', '#006200', '#004e00', '#003b00', '#002700']

#iterate through the Pct_Green field to apply the symbology based on the percentage value
for i in range(len(breaks)-1):
    min_break = breaks[i]
    max_break = breaks[i+1]
    sym = QgsSymbol.defaultSymbol(lyr.geometryType())
    sym.setOpacity(0.6)
    sym.setColor(QtGui.QColor(color_sym[i]))
    range_label = str(breaks[i]) + ':' + str(breaks[i+1]) + '%'
    rangeList.append(QgsRendererRange(min_break, max_break, sym, range_label))
renderer = QgsGraduatedSymbolRenderer(field_name, rangeList)
lyr.setRenderer(renderer)
lyr.triggerRepaint()

#create a layout with the map, title, scale bar, legend, and north arrowHeadFillColor
lyr_to_display = QgsProject.instance().mapLayersByName('Neighbourhoods_GreenSpaces_UTM17')[0]
proj = QgsProject.instance()
mgr = proj.layoutManager()
layout_name = 'GreenSpace_per_Neighbourhood'

for lyt in mgr.layouts():
    if lyt.name() == layout_name:
        mgr.removeLayout(lyt)
        
lyt = QgsPrintLayout(proj)
lyt.initializeDefaults()
lyt.setName(layout_name)
mgr.addLayout(lyt)
map = QgsLayoutItemMap(lyt)
map.setRect(QRectF(10,10,10,10))
ms = QgsMapSettings()
ms.setLayers([lyr_to_display])

#Extent
extent_rect = QgsRectangle(609000.0,4825000.0, 652000.0,4857449.0)
map.setExtent(extent_rect)
ms.setExtent(extent_rect)
lyt.addLayoutItem(map)
map.setBackgroundColor(QColor(255, 255, 255))
map.attemptMove(QgsLayoutPoint(10, 20, QgsUnitTypes.LayoutMillimeters))
map.attemptResize(QgsLayoutSize(150,150, QgsUnitTypes.LayoutMillimeters))

#add layout title
title=QgsLayoutItemLabel(lyt)
title.setText("Toronto Percent Green Spaces Per Neighbourhood")
title.setFont(QFont("Georgia",20,QFont.Bold))
title.adjustSizeToText()
lyt.addLayoutItem(title)
title.attemptMove(QgsLayoutPoint(55,7,QgsUnitTypes.LayoutMillimeters))

#add the legend
legend = QgsLayoutItemLegend(lyt)
legend.setLinkedMap(map) # map is an instance of QgsLayoutItemMap
legend.setTitle('Percentage Ranges')
#set up the layer tree to add only those layers to the legend that I specify (only the green spaces
#per neighbourhood will be shown)
layerTree = QgsLayerTree()
layerTree.addLayer(lyr_to_display)
layerTree.setName('')
legend.model().setRootGroup(layerTree)
legend.updateLegend()
#add the legend to the layout
lyt.addLayoutItem(legend)
#move the legend to the specified area to the right of the map
legend.attemptMove(QgsLayoutPoint(170, 20, QgsUnitTypes.LayoutMillimeters))

#add the scale bar
sb = QgsLayoutItemScaleBar(lyt)
sb.setStyle('Double Box')#set the scale bar style to double box
sb.setUnits(QgsUnitTypes.DistanceKilometers)#set the units to meters
sb.setNumberOfSegments(4)#create a scale bar with 4 segments
sb.setNumberOfSegmentsLeft(0)#all of the segments will be to the right, 0 will be to the left
sb.setUnitsPerSegment(5)#each segment will represent 2 kilometres
sb.setUnitLabel('km')
sb.setFont(QFont('Georgia', 8))#set the font of the scale bar's text to Georgia
sb.setLinkedMap(map) #map is an instance of QgsLayoutItemMap
#sb.applyDefaultSize()
lyt.addLayoutItem(sb)
sb.attemptMove(QgsLayoutPoint(10, 180, QgsUnitTypes.LayoutMillimeters))
sb.attemptResize(QgsLayoutSize(200,200, QgsUnitTypes.LayoutMillimeters))

#add a photo of a Toronto park (variable is ph for photo)
ph = QgsLayoutItemPicture(lyt)
ph.setMode(QgsLayoutItemPicture.FormatRaster)
ph.setPicturePath("C:/temp/img/Toronto-Park.jpg")
ph.attemptMove(QgsLayoutPoint(175, 104, QgsUnitTypes.LayoutMillimeters))
ph.attemptResize(QgsLayoutSize(1200,950, QgsUnitTypes.LayoutPixels))
lyt.addLayoutItem(ph)

#add a north arrow (variable for north arrow is na)
na=QgsLayoutItemPicture(lyt)
na.setMode(QgsLayoutItemPicture.FormatSVG)
na.setPicturePath("C:/temp/img/North-Arrow.png")
na.attemptMove(QgsLayoutPoint(120, 130, QgsUnitTypes.LayoutMillimeters))
na.attemptResize(QgsLayoutSize(*[450,450], QgsUnitTypes.LayoutPixels))
lyt.addLayoutItem(na)

#export the layout to a PDF in the C:/temp folder
lyt = mgr.layoutByName(layout_name)
exporter = QgsLayoutExporter(lyt)
fn = 'C:/temp/GreenSpace_by_Neighbourhood.pdf'
exporter.exportToPdf(fn, QgsLayoutExporter.PdfExportSettings())
print('Processing complete. Check C:/temp for the PDF that was created')