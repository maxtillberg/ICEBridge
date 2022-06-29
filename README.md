# ICEBridge
Blender plugin to send BIM data to IDA ICE

Installation
Download ICEBridge.py and install a normal Blender plugin. Instructions can be found here https://docs.blender.org/manual/en/latest/editors/preferences/addons.html

Usage
1. Create or import BIM- or CAD-data to Blenderb
2. Make sure that the data is valid
  a. Zones and Building bodies must be made up of closed volumes made of planar surfaces.
  b. Windows and doors works best if they are planar
3. Select objects of one type, for example zones.
4. Select the corresponding opject type in ICEBridge, path and press "Export to IDA ICE". This will generate a script file and geoemtry files
5. Open IDA ICE and run the generated script

Limitations
This is a proof of concept, not an official product by Equa. There will be bugs and limitations.
- Windows and doors must be rectangular.
- Windows and doors can only be placed in buisling bodies. Windows can be moved to zones manually.
- Sloped roof windows can be smaller then the original windows.

Input
ICEBridge works well with BlenderBIM and Speckle but any valid geoemtry will work.
