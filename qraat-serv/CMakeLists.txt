cmake_minimum_required(VERSION 2.8)

# Install base 'qraat' module.
# TODO uninstall trigger.
install(CODE "execute_process(COMMAND python setup.py install 
--prefix=${CMAKE_INSTALL_PREFIX}
WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})")

# Descend into serv/ 
add_subdirectory(serv)
