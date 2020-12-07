#!/bin/python3
import argparse
import copy
import hashlib
import json
import os
import urllib.request
import urllib.parse
import re
import tarfile
import yaml
from typing import *
from os.path import basename, dirname, exists, join, relpath
from collections import OrderedDict


PKG_FILE = "minecraft_pkg.yml"
DATA_FILE = "mods.json"
VAR_C = re.compile(r'\$(\w+|\{[^}]*\})', re.ASCII)


def expandvar(texte, contexte):
	global var
	i = 0
	while i < len(texte):
		m = VAR_C.search(texte)
		if m is None:
			break
		i, j = m.span(0)
		nom = m.group(1)
		if nom.startswith("{") and nom.endswith("}"):
			nom = nom[1:-1]
		valeur = contexte.get(nom, "??")
		texte = texte[:i] + valeur + texte[j:]
		i += len(valeur)
		
	return texte


def clean(ENV):
	os.remove(ENV["builddir"])


class DownloadFile:
	def __init__(self, ENV: dict, src: str, target: str):
		self.filename = join(ENV['pkgdir'], expandvar(target, ENV))
		self.url = urllib.parse.urljoin(f"file:{ENV['workdir']}/", expandvar(src, ENV))
		
	def skip(self) -> bool:
		return exists(self.filename)
		
	def __call__(self):
		print(f"Download {self.url}", end="")
		if not exists(dirname(self.filename)):
			os.makedirs(dirname(self.filename))
		
		with urllib.request.urlopen(self.url) as request:
			with open(self.filename + ".part", "wb") as dest:
				dest.write(request.read())

		os.rename(self.filename + ".part", self.filename)
		print("\tOK")


class DownloadAllFiles:
	def __init__(self, ENV: dict, sources: dict):
		self.downloads = list()
		
		assert isinstance(sources, dict)
		for file, url in sources.items():
			# if only a directory is given (ends with '/'), completes with the filename found in the url
			if basename(file) == "":
				url_parse = urllib.parse.urlparse(url)
				file = join(file, basename(url_parse.path))
		
			self.downloads.append(DownloadFile(ENV, url, file))
	
	def skip(self) -> bool:
		return all(d.skip() for d in self.downloads)
		
	def __call__(self):
		for d in self.downloads:
			if not d.skip():
				d()


def create_hash(pkgdir):
	hashs = dict()
	dirs = [pkgdir]
	while len(dirs) > 0:
		directory = dirs.pop()
		for filename in map(lambda f: join(directory, f), os.listdir(directory)):
			if basename(filename).startswith(".") or relpath(filename, pkgdir) == "mods.json":
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
	if isinstance(v, (int, float)):
		return str(v)
	elif v is None or v.lower() == "any" or v.lower() == "all":
		return "(,)"
	else:
		return v


class GenerateInfoFile:
	def __init__(self, ENV: Dict[str, str], data: Dict[str, str]):
		self.pkgdir = ENV["pkgdir"]
		self.pkg_data = dict()
		self.pkg_data["name"] = data["name"]
		self.pkg_data["displayName"] = data["displayName"]
		self.pkg_data["version"] = str(data["version"])
		self.pkg_data["description"] = data["description"]
		self.pkg_data["section"] = data.get("section", "any")
		if "url" in data:
			self.pkg_data["url"] = data["url"]
		
		self.pkg_data["dependencies"] = dict(map(lambda d: (d[0], _check_version(d[1])), data["depends"].items()))
		self.pkg_data["conflicts"] = dict(map(lambda d: (d[0], _check_version(d[1])), data.get("conflicts", dict()).items()))
		self.pkg_data["files"] = dict()
		
		self.download = DownloadAllFiles(ENV, data.get("sources", dict()))
		
	def skip(self):
		return self.download.skip()
	
	def __call__(self):
		if not self.download.skip():
			self.download()
		print(f"Data {pkgdata['name']}-{pkgdata['version']}", end="")

		for filename, sha in create_hash(self.pkgdir).items():
			self.pkg_data["files"][filename] = dict()
			self.pkg_data["files"][filename]["sha256"] = sha.hex()

		with open(join(self.pkgdir, DATA_FILE), "w") as MODS:
			json.dump(self.pkg_data, MODS, sort_keys=False, indent=4)
		print("\tOK")


def tar(ENV: dict, pkg_data: dict):
	print(f"Tar {pkgdata['name']}-{pkgdata['version']}", end="")
	tar_filename = join(ENV['workdir'], "{}-{}.tar".format(pkg_data["name"], pkg_data["version"]))
	with tarfile.open(tar_filename, "w") as file:
		for filename in os.listdir(ENV['pkgdir']):
			file.add(join(ENV['pkgdir'], filename), arcname=filename)
	print("\tOK")


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("pkgfile", nargs="+")
	parser.add_argument("--builddir", type=str, default="build")
	parser.add_argument("-D", nargs="*", help="Add environment variables")

	args = parser.parse_args()
	G_ENV: Dict[str, str] = dict()
	
	if args.D is not None:
		for var in args.D:
			if "=" in var:
				k, v = var.split("=")
				G_ENV[k] = v
	
	G_ENV['builddir'] = os.path.abspath(args.builddir)

	if not exists(args.builddir):
		os.makedirs(args.builddir)
	
	for pkgfile in args.pkgfile:
		with open(pkgfile, "r") as config:
			packet_list = list(yaml.load_all(config, Loader=yaml.SafeLoader))

		for pkgdata in packet_list:
			assert pkgdata is not None
			assert "name" in pkgdata
			assert "displayName" in pkgdata
			assert "version" in pkgdata
			assert "description" in pkgdata
		
			pkgdir = join(args.builddir, "{}-{}".format(pkgdata["name"], pkgdata["version"]))
			ENV = copy.deepcopy(G_ENV)
			ENV["workdir"] = dirname(pkgfile)
			ENV['pkgdir'] = pkgdir
			ENV["version"] = pkgdata["version"]
			ENV["name"] = pkgdata["name"]
			ENV["displayName"] = pkgdata["displayName"]
			
			build = GenerateInfoFile(ENV, pkgdata)
			if not build.skip():
				build()
				tar(ENV, pkgdata)
			else:
				print(f"{pkgdata['name']}-{pkgdata['version']} skipped")
