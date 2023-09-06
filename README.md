# bxf_merge - batch import *.bxf2 files into BAZIS CAD
## What is a BXF file?
The BXF file (Blum Exchange Format) not only contains information about the fitting, but also manufacturing information for wooden parts, such as cutting dimensions and drilling positions. The BXF file is created by the Product Configurator and Cabinet Configurator, which you can then import into your CAD software for further planning.

BXF is compatible with an increasing number of partner software products and can be easily transferred to drilling and insertion machines with EASYSTICK.

## What is BAZIS?
BAZIS - CAD/CAM software solutions for furniture design, manufacturing and marketing

In our manufacture we use both bxf and bazis a lot. Information about every working part that needs to be produced is contained within bxf file. As BAZIS CAD doesn't support importing multiple BXF files in one time, i wrote small script to make one bxf that contains all useful information from several selected bxf's. Finally we can import this one bxf that contains several parts all at once! Isn't that cool? No? Oh, get lost, i really love it 💚
