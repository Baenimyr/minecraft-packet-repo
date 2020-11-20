#!/bin/python3
import urllib.request
import urllib.parse
import hashlib
import yaml
import json
import os
import tarfile
import argparse
from typing import *
from os.path import basename, dirname, exists, join, relpath
from collections import OrderedDict


PKG_FILE = "minecraft_pkg.yml"
DATA_FILE = "mods.json"


def clean(ENV):
	os.remove(ENV["builddir"])


def download_file(ENV: dict, src: str, target: str):
	filename = join(ENV['pkgdir'], target)
	if not exists(dirname(filename)):
		os.makedirs(dirname(filename))
	
	if not exists(filename):
		url = urllib.parse.urljoin(f"file:{ENV['workdir']}/", src)
		with urllib.request.urlopen(url) as request:
			with open(filename + ".part", "wb") as dest:
				dest.write(request.read())

		os.rename(filename + ".part", filename)
		print(f"- {target}\tOK")
	else:
		print(f"- {target}\tSKIPPED")


def download(ENV: dict, pkgdata: dict):
	sources = pkgdata.get("sources", dict())
	assert isinstance(sources, dict)
	print("Download")
	for file, url in sources.items():
		# if only a directory is given (ends with '/'), completes with the filename found in the url
		if basename(file) == "":
			url_parse = urllib.parse.urlparse(url)
			file = join(file, basename(url_parse.path))
	
		download_file(ENV, url, file)


def create_hash(ENV: dict):
	pkgdir = ENV["pkgdir"]

	hashs = dict()
	dirs = [pkgdir]
	while len(dirs) > 0:
		directory = dirs.pop()
		for filename in map(lambda f: join(directory, f), os.listdir(directory)):
			if basename(filename).startswith("."):
				continue
			elif os.path.isfile(filename):
				with open(filename, "rb") as file_content:
					sha = hashlib.sha256()
					sha.update(file_content.read())
					hashs[relpath(filename, pkgdir)] = sha.digest()
			elif os.path.isdir(filename):
				dirs.append(filename)
	
	return hashs


def _check_version(v) -> str:
	if v is None or v.lower() == "any" or v.lower() == "all":
		return "(,)"
	else:
		return v


def gen_MOD(ENV: Dict[str, str], data: Dict[str, str]):
	print("Data", end="")

	pkg_data = dict()
	pkg_data["name"] = data["name"]
	pkg_data["displayName"] = data["displayName"]
	pkg_data["version"] = data["version"]
	pkg_data["url"] = data["url"]
	pkg_data["description"] = data["description"]
	pkg_data["section"] = data["section"]

	data.setdefault("depends", dict())
	data.setdefault("conflicts", dict())
	pkg_data["dependencies"] = dict(map(lambda d: (d[0], _check_version(d[1])), data["depends"].items()))
	pkg_data["conflicts"] = dict(map(lambda d: (d[0], _check_version(d[1])), data["conflicts"].items()))

	pkg_data["files"] = dict()
	for filename, sha in create_hash(ENV).items():
		pkg_data["files"][filename] = dict()
		pkg_data["files"][filename]["sha256"] = sha.hex()

	with open(join(ENV['pkgdir'], DATA_FILE), "w") as MODS:
		json.dump(pkg_data, MODS, sort_keys=False, indent=4)
	print("\tOK")


def tar(ENV: dict, pkg_data: dict):
	print("Tar", end="")
	tar_filename = join(ENV['workdir'], "{}-{}.tar".format(pkg_data["name"], pkg_data["version"]))
	with tarfile.open(tar_filename, "w") as file:
		for filename in os.listdir(ENV['pkgdir']):
			file.add(join(ENV['pkgdir'], filename), arcname=filename)
	print("\tOK")


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("workdir", type=str, default=".")
	parser.add_argument("--pkgfile", type=str, default=PKG_FILE)
	parser.add_argument("--builddir", type=str, default="build")

	args = parser.parse_args()
	ENV: Dict[str, str] = dict()
	ENV['workdir'] = os.path.abspath(args.workdir)
	ENV['pkgfile'] = args.pkgfile
	ENV['builddir'] = os.path.abspath(args.builddir)

	if not exists(args.builddir):
		os.makedirs(args.builddir)
	
	with open(join(args.workdir, ENV['pkgfile']), "r") as config:
		packet_list = list(yaml.load_all(config, Loader=yaml.SafeLoader))

	for pkgdata in packet_list:
		pkgdir = join(args.builddir, "{}-{}".format(pkgdata["name"], pkgdata["version"]))
		ENV['pkgdir'] = pkgdir
		
		download(ENV, pkgdata)
		gen_MOD(ENV, pkgdata)
		tar(ENV, pkgdata)
