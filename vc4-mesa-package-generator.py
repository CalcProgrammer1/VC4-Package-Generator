#
#	Mesa Git Packaging Script for Debian Unstable
#
#	This script will create Debian (unstable) packages for Mesa from upstream git sources.
#	It will skip building swx11 versions of the Mesa libraries as these are not used in systems with a GPU
#	By default this script expects the Debian version to use llvm (and libclang) 3.5 and will change it to use llvm 3.7
#	If Debian updates their copy to use a different llvm version, or if a new version of llvm is released, this script must be updated
#
#	This script has been modified to add support for the Broadcom VideoCore IV "vc4" driver, to be used on the Raspberry Pi.
#	This script should work on Raspbian Testing, Debian Testing, and Debian Unstable.  You may need to change LLVM versions.
#
#	The system as well as the chroot must have build-essential and devscripts installed
#
#	Written by Adam Honse (calcprogrammer1) 12/9/2015
#

# This sets the existing version (which the upstream packages build off of) and the replacement version (use the latest available LLVM)
llvm_existing_version = "3.5"
llvm_replacement_version = "3.7"

# This is the URL to clone for the upstream mesa source code
git_mesa_url = "git://anongit.freedesktop.org/mesa/mesa"

import os

print "Create mesa working directory"

rootdir = os.popen("pwd").read().strip("\n")
os.popen("rm -r mesa-vc4").read()
os.mkdir("mesa-vc4")
os.chdir(rootdir + "/mesa-vc4")

print "Update apt sources"
os.popen("apt-get update").read()

print "Download mesa official sources"
os.popen("apt-get source mesa").read()

print "Save original folder name"
for file in os.listdir(rootdir + "/mesa-vc4"):
	if os.path.isdir(file):
		orig_name = file

orig_path = rootdir + "/mesa-vc4/" + orig_name + "/"

print "Print original name"
print orig_name

print "Clone upstream mesa from git"
os.popen("git clone " + git_mesa_url + " mesa").read()

print "Get revision"
os.chdir(rootdir + "/mesa-vc4/mesa")
git_version = os.popen("git rev-parse --short HEAD").read().rstrip()
print git_version

print "Move git mesa directory"
os.chdir(rootdir + "/mesa-vc4")
new_name = orig_name + "-" + git_version
new_path = rootdir + "/mesa-vc4/" + new_name + "/"
print new_path
os.rename(rootdir + "/mesa-vc4/mesa", new_path)

print "Copy debian folder"
os.chdir(rootdir + "/mesa-vc4")
os.popen("cp -rp " + orig_path + "debian" + " " + new_path + "debian").read()

print "Remove patches"
os.chdir(new_path + "debian/patches")
os.popen("rm *").read()
os.popen("touch series")

print "Update debian/control file"

f1 = open(new_path + "debian/control",     'r')
f2 = open(new_path + "debian/control.tmp", 'w')

swx11_block = 0

for line in f1:

	if swx11_block == 0:
		#Look for Package and swx11 in the same line
		if "Package" in line and "swx11" in line:
			#If inside swx11 block, do not write to new file until we see Package again
			swx11_block = 1

		else:
			#Look for llvm and libclang 3.7, replace with 3.8
			line = line.replace("llvm-" + llvm_existing_version + "-dev", "llvm-" + llvm_replacement_version + "-dev")
			line = line.replace("libclang-" + llvm_existing_version + "-dev", "libclang-" + llvm_replacement_version + "-dev")

			#Write out modified line
			f2.write(line)

	elif swx11_block == 1:
		#If we see "Package" we know we are in a new block, so start writing again
		if "Package" in line and not "swx11" in line:
			swx11_block = 0
			f2.write(line)

f1.close()
f2.close()

os.remove(new_path + "debian/control")
os.rename(new_path + "debian/control.tmp", new_path + "debian/control")

print "Update debian/rules file"

f1 = open(new_path + "debian/rules",     'r')
f2 = open(new_path + "debian/rules.tmp", 'w')

#Read through all lines in rules file and edit them as necessary
for line in f1:

	#Look for llvm and libclang 3.7, replace with 3.8
	line = line.replace("llvm-config-" + llvm_existing_version, "llvm-config-" + llvm_replacement_version)

	#Look for swx11 and replace it with empty string (to disable building swx11)
	line = line.replace("swx11-i386-i686", "")
	line = line.replace("swx11-static", "")
	line = line.replace("swx11", "")

	#Look for freedreno and add vc4 (as freedreno will be selected on ARM platforms, just like vc4 should)
	line = line.replace("freedreno", "freedreno vc4")

	#Fix removal error during build
	line = line.replace("do rm debian", "do rm -f debian")

	#Write out modified line
	f2.write(line)

f1.close()
f2.close()

os.remove(new_path + "debian/rules")
os.rename(new_path + "debian/rules.tmp", new_path + "debian/rules")

print "Update changelog"
os.chdir(new_path)
os.popen("dch -d \"git commit " + git_version + "\"").read()

print "Install build dependencies"
os.system("mk-build-deps --tool \"apt-get --no-install-recommends -y\" --install " + new_path + "debian/control")

print "Begin building"
os.system("dpkg-buildpackage")

print "It probably had an error due to missing symbols.  Update the symbols files"
os.system("dpkg-gensymbols -plibegl1-mesa -Pdebian/libegl1-mesa -Odebian/libegl1-mesa.symbols")
os.system("dpkg-gensymbols -plibgles2-mesa -Pdebian/libgles2-mesa -Odebian/libgles2-mesa.symbols")
os.system("dpkg-gensymbols -plibxatracker2 -Pdebian/libxatracker2 -Odebian/libxatracker2.symbols")

print "Resume building"
os.system("dpkg-buildpackage -nc")
