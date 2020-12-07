MAKEPKG=python3 makepkg.py

.PHONY: optifine ctm main

clean:
	rm -r build

optifine:
	@$(MAKEPKG) graphic/optifine_pkg.yml -Dsrcdir=$(SRCDIR)
	
ctm:
	@$(MAKEPKG) graphic/ctm_pkg.yml -Dsrcdir=$(SRCDIR)
	
main:
	@$(MAKEPKG) main/i/immersiveengineering.yml main/r/refinedstorage.yml main/s/storagedrawers.yml -Dsrcdir=$(SRCDIR)
	
all: optifine ctm main
