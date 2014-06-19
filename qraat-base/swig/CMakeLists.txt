# setup.py creates the "pulse_data.py" interface we want, but doesn't
# put it in the right place. This one-liner is meant as a work-around.  
FIND_PACKAGE(PythonLibs)
INSTALL(FILES ${CMAKE_CURRENT_SOURCE_DIR}/pulse_data.py
        DESTINATION /usr/local/lib/python2.7/dist-packages/qraat)
# FIXME this should be removable. 
