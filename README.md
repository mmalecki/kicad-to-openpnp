# kicad-to-openpnp

**Note: this is heavily WIP, and may introduce ghosts into your machine.**

`kicad-to-openpnp` helps you convert your KiCad project into a set of full-fledged
OpenPnP packages and parts, including pin definitions, as well as dimensions
taken from 3D models of the footprints.

It does *not* replace OpenPnP's KiCad position file import process, it enhances it.

## Installation

Prerequisites:
* KiCad
* CadQuery

Installation instructions TBD.

## Usage
In my workflow, I generate separate `packages.xml` and `parts.xml` files for each
job. This simply helps me keep OpenPnP drop-downs free of clutter. Feel free to do
otherwise, but the following guide follows this principle.

In your KiCad project directory:

```sh
kicad-to-openpnp -b my_board.kicad_pcb

# Make backups of existing packages.xml and parts.xml if you wish.

cp packages.xml parts.xml ~/.openpnp2
```

That's it! Make sure to verify all the dimensions, as wrong height can potentially
cause machine crashes or job interruptions.
