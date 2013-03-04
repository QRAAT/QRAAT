#/bin/bash
# Chris ~1 Mar 2013
#
# Manage site configuration CSV file. See notes/sitelist.csv for an example
# site list. I put this here for testing purposes. This will be integrated into 
# rmg script.
#

file=$1 
site=$2 
key=$3
value=$4

if [ ! $key ] 
  then
    echo "usage: guy <file> <site> <key> [<value>]"
    exit 1
  fi

if [ ! $value ]
  then # read
    
    perl -e "while (\$_ = <>) { 
      print \"\$1\n\" if (!/^\s*\#/ && \$_ =~ /name=\"$site\".*$key=\"([^\"]+)\"/) 
        }" < $file
  
  else # write

    perl -pe "s/$key=\"[^\"]+\"/$key=\"$value\"/g 
        if (!/^\s*\#/ && /name=\"$site\"/)" < $file > tmp_$file

    mv tmp_$file $file

fi

