# toronto-GS-NB
This script makes use of the QGIS Python API to create a map showing the percentage of Toronto's 152 neighbourhoods that is comprised of green spaces
The GIS processes that are done using Python are as follows:
1) Ingests the shapefiles downloaded from the City of Toronto Open Data Portal needed for this analysis: 
  a) Green Spaces (https://open.toronto.ca/dataset/green-spaces/)
  b) Neighbourhoods (https://open.toronto.ca/dataset/neighbourhoods/)
2) Adds the Google basemap to the QGIS Project
3) Reprojects the shapefiles (which currently need to be saved to C:/temp) from WGS84 to UTM17 so that area calculations using metres can be done later in the script
4) Caclulate the area for each neighbourhood in the re-projected neighbourhoods shapefiel
5) Use the Intersect tool to find where the green spaces intersect the neighbourhood boundaries. This will tell us which green spaces are in which neighbourhood
6) Use the QGIS Repair tool to fix any invalid geometries (you may receive an error if the Repair tool is not run).
7) Using the Dissolve tool, create a multipart polygon of green spaces for each neighbourhood
8) Calculate the area of the dissolved green space polygons. This will give us the area of green space in square kilometres per neighbourhood.
9) Join the result of the dissolve tool (shown as dissolve_shp in the code) to the neighbourhoods shapefile using the area code (aka AREA_SHORT).
10)Calcuate the percentage of green space per neighbourhood by dividing the area of the green spaces per neighbourhoods by the total area of the neighbourhoods then multiply that result by 100
11) Symbolize the output layer by percentage of green space using breaks of 0,5,10,20,30,40,50,60,70
12) Create a layout (variable = lyr)--a) determine the map extent; b) add the map frame to the layout; c) add the layout's title; d) add the map legend; e) add the map scale bar; f) add a photo (the script will look for "C:/temp/img/Toronto-Park.jpg"--the photo I used can be downloaded from https://www.pexels.com/photo/people-walking-on-park-near-tower-137581/); g) add a north arrow to the map layout
13) Export the map layout that was just created to C:/temp/GreenSpace_by_Neighbourhood.pdf

The goal is to ultimately create a plug-in that would allow the user to add the files from a location they choose, but for now the file locations of the input files are hardcoded 
