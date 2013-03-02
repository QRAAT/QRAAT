#!/bin/bash
# rmg_vars
# This script is part of the QRAAT system. It provides system variables
# for running QRAAT.
#
# Copyright (C) 2013 Todd Borrowman
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

RMG_SERVER_DIR="/rmg_server"
export RMG_SITE_METADATA_DIR="/home/rmg"
export RMG_SITE_DET_DIR="/tmp/ramdisk/det_files"
export RMG_SERVER_SSH_KEYFILE="/home/rmg/.ssh/rmg_rsa"
export RMG_SERVER_DET_DIR="$RMG_SERVER_DIR/det_files"
export RMG_SERVER_EST_DIR="$RMG_SERVER_DIR/est_files"
export RMG_SERVER_SITELIST="$RMG_SERVER_DIR/rmg_sitelist.csv"


