SupCom_Import_Export_Blender
============================

Python scripts to import and export Supreme Commander units (.scm) and animations (.sca) in Blender.

Setting up the plugins :
------

There are two branches, one for 2.79- which is working and stable. The version for 2.80+ is under development and barely working at all. Select the version you want from the branches dropdown, and download the importer and exporter files. They are counted as separate plugins.

These scripts are installed just like other blender plugins:
You can then place them into your plugins directory: `BlenderInstallDir/BlenderVersion/scripts/addons`
Then you can enable them in the user preferences, in the plugins section. There will be two plugins, import and export, under the Import/Export category.

Importing :
------
- You can import .scm models from Supreme commander, find the corresponding model in the game files (units.scd)

- To import animations (.sca), you have to have already loaded a model on Blender, either the corresponding mesh (.scm), or a custom mesh of your own, with the bones corresponding in names with the animation bones (each bone named in the animation must have a corresponding one with the same name in the mesh).

Exporting :
------

- When creating a new unit, the central bone (parent of all other bones of the armature) of the unit must have the same name as the unit.

- The exporter deals with one armature at a time. You can hide any armatures you dont want to be taken into account.

- All vertices must be in a "Vertex Group", and each vertex group must have the name of a bone. If some vertices are not moving, just assign them to the group with the base bone as bonename. The exporter will put you into edit mode and select the first non-assigned vertex if your mesh contains them.

- An animation must be associated with an action (see the NLA editor).

- When exporting, the script will assume the unit name (and so the .scm filename) from the central bone, and the filename for the animation from the action name in Blender (can be seen in the NLA editor). So you'll have only to select the output folder, filenames will be deduced.

- All faces must be triangles. No quads or ngons. The exporter will put you into edit mode and highlight the first non-triangle if your mesh contains them.

- Vertices at the same location will be merged, unless they are part of a sharp edge. Supcom uses merged vertices for smooth shading. To get hard shading, set the required edges to sharp, and then split them. The exporter will not merge them together.

known bugs :
Order of bones are not respected at export.
All animations are exported as separate files, but they all contain the same active animation. Currently you must export them multiple times, once for each animation, and rename files to prevent overwriting.
Blender 2.80 support status: supcom model importing works, nothing else works.

Credits to dan & Brent for the original version and all the engineering work. Thanks to Oygron for porting it to 2.71.
My work has only been to help out with edge sharpness and pending 2.80 support.
