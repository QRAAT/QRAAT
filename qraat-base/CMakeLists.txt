cmake_minimum_required(VERSION 2.8)

# Install base 'qraat' module.
install(CODE "execute_process(COMMAND python setup.py install 
--prefix=${CMAKE_INSTALL_PREFIX}
WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})")

########################################################################
# Add subdirectories
########################################################################
add_subdirectory(include)
add_subdirectory(lib)
add_subdirectory(swig)
#add_subdirectory(grc)
#add_subdirectory(apps)
add_subdirectory(serv)
