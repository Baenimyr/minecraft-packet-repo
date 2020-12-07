# MinecraftPacket Repo

## Repositories
Build in progress
- [graphic](/graphic/README.md)


## Build script
`makepkg.py` can help you building a packet.
Create a yml file where you want and use the command below to build all the packages declared in the file.
```sh
python3 makepkg.py DIR/file.yml
```

You can declare external variables like `srcdir` with the command `-Dsrcdir=...`.

### Fields
- name: the universal identifier (_modid_ in MinecraftForge)
- displayName: a more common name
- version: the version of the packet
- section: on of _any_ (default), _mod_, _resource_, _shader_, _config_, _modpack_
- description
- sources: all the files to include in the packet in the format `DEST_DIR/: FILE_URL` or `DEST_DIR/FILENAME: FILE_URL`. The file's url accepts the protocols http or local file by default. The destination folder is relative to the _.minecraft_ folder.
- depends: all the dependencies
- conflicts: the packets in conflict with this one.

Sources are optional if you want to create a metapacket.

For exemple
```yml
# This is optifine for Forge 1.16.3
name: optifine-forge
displayName: Optifine
version: 1.16.3-G3
section: mod
url: https://optifine.net
description: |-
    OptiFine is a Minecraft optimization mod.
    It allows Minecraft to run faster and look better with full support for shaders, HD textures and many configuration options.
sources:
    "mods/": OptiFine_1.16.3_HD_U_G3.jar
depends:
    forge: "[34.1.42,35)"
    minecraft: 1.16.3
conflicts:
    sodium: all  # for the example: Optifine fabric is in conflit
    lithium: "(,)"
---
name: ...
```

#### Note on name
Please use `_` rather than `-` in the rest of the name, `-` must be kept for special naming like below.

If you want to make distinction between forge and fabric add `-forge` or `-fabric` at the end of the name, not at the beginning.
This way the real modid is present first, like in `optifine-forge` or `optifine-fabric`.
