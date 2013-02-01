#!/bin/bash
#proc_det.sh
#script for running the run_rmg script through cron and processing the files generated
#performs the following steps
#    stops the current run_rmg process
#    moves .det from $RAMDISK/det_files to $RAMDISK/det_files_YYYYMMDD if exists
#    starts new run_rmg process using $RMG_CONFIG .conf file
#    produces .est at $EST_DIR from $RAMDISK/det_files_YYYYMMDD
#    produces .csv at $CSV_DIR from $RAMDISK/det_files_YYYYMMDD
#    produces .tar archive of $RAMDISK/det_files_YYYYMMDD at $TAR_DIR
#    deletes $RAMDISK/det_files_YYYYMMDD
#
# 04/2012 TAB


echo "Running proc_det.sh on $(date)"

RAMDISK=/tmp/rmg_ramdisk
RMG_CONFIG=/rmg_data/rmg.conf
EST_DIR=/rmg_data/est
CSV_DIR=/rmg_data/csv
TAR_DIR=/rmg_data/tar
PYTHON_DIR=/usr/local/lib/python2.7/dist-packages
#the python directory should be found dynamically or found during installation

cd $RAMDISK

#find run_rmg process name if running
pgrep -f -l run_rmg > tmp1
RMG_PID=`awk '{print $1}' < tmp1`
RMG_ARGS=`awk 'BEGIN {FS="run_rmg.py "}{print $2}' < tmp1`
rm tmp1

#stop run_rmg if running
if [ $RMG_PID ]
  then
    echo "Stopping RMG"
    kill $RMG_PID
  else
    echo "RMG not running"
fi

#if there are det files at /tmp/rmg_ramdisk/det_files/ to /tmp/rmg_ramdisk/det_files_YYYYMMDD/
if [ -d det_files ]
  then
    MV_DET_DIR=det_files_$(date +%Y%m%d%H%M)
    mv det_files $MV_DET_DIR
    echo "Moved det_files to $MV_DET_DIR"
  else
    echo "No det_files directory"
fi
mkdir det_files\

#start run_rmg
if [ -f $RMG_CONFIG ]
  then
    #Using defaults
    echo "Using rmg.conf defaults"
    if [ ! -d $RAMDISK/det_files ]
      then
        echo "Making $RAMDISK/det_files"
        mkdir $RAMDISK/det_files
    fi
    echo "Starting RMG"
    $PYTHON_DIR/run_rmg.py `cat $RMG_CONFIG` &>$RAMDISK/det_files/running_rmg.txt &
  else
    if [ $RMG_ARGS ]
      then
        #Using previous config
        echo "Using previous running RMG configuration"
        if [ ! -d $RAMDISK/det_files ]
          then
            echo "Making $RAMDISK/det_files"
            mkdir $RAMDISK/det_files
        fi
        echo "Starting RMG"
        $PYTHON_DIR/run_rmg.py $RMG_ARGS &>$RAMDISK/det_files/running_rmg.txt &
      else
        echo "No default or previous configuration for RMG.  Not starting RMG."
    fi
fi

#create .est files from /tmp/rmg_ramdisk/det_files_YYYYMMDD/ to /rmg_data/est/
if [ $MV_DET_DIR ]
  then
    echo "Creating est files at $EST_DIR"
    $PYTHON_DIR/process_det.py $RAMDISK/$MV_DET_DIR $EST_DIR $CSV_DIR
fi


#save .det files in .tar at /rmg_data/tar/ if defined
if [ -d $TAR_DIR -a -n "$MV_DET_DIR" ]
  then
    echo "Creating $TAR_DIR/$MV_DET_DIR.tar.gz"
    tar -czf $TAR_DIR/$MV_DET_DIR.tar.gz $MV_DET_DIR
fi

#remove det files from ramdisk
if [ $MV_DET_DIR ]
  then
    echo "Removing $MV_DET_DIR"
    rm -r $RAMDISK/$MV_DET_DIR
fi

echo
echo

