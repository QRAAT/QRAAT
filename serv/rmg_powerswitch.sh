#!/bin/bash
# 
# Chris ~4 Mar 2013
# rmg_powerswitch.sh
# Site-specific power management stuff.
# 

TYPE=$1
IP=$2
OUTLET=$3
OP=$4

if [ ! $OP ]
then
  echo "usage: powerswitch <power_type> <IP_addr> <outlet> {ON, OFF, CYCLE}" 1>&2
  exit 1
fi 

function webpowerswitch {
  # This is the big, clunky network addressible power supply that Marcel 
  # modified. It now supplies 12 V DC to 10 outlets. It's not easily 
  # scripted via telnet, so here we use curl. 
  case $OP in

    ON|OFF) 
    ;; 

    CYCLE) 
      OP="CCL"
      echo "powerswitch: Wait about 15 seconds for power to cycle."

    ;;

    *) 
      echo "error (powerswitch): '$OP' is not a valid operation." 1>&2
      exit 1
    
  esac
  
  curl --user admin:1234 "http://$IP/outlet?$OUTLET=$OP" > /dev/null

}


## execute power script ## 
case $TYPE in
  
  webpowerswitch) 
    webpowerswitch
  ;;

  # more to come!

  *)
    echo "error (powerswitch): '$TYPE' is not a valid power type." 1>&2
    exit 1
  ;;

esac
