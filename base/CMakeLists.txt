cmake_minimum_required(VERSION 2.8)

# Install base 'qraat' module.

add_custom_target(pulse_data ALL
                  COMMAND python setup.py clean --all
                  COMMAND python setup.py build
                  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})

install(CODE "execute_process(COMMAND python setup.py install 
--prefix=${CMAKE_INSTALL_PREFIX}
WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})")

########################################################################
# Add subdirectories
########################################################################
add_subdirectory(include)
add_subdirectory(lib)
add_subdirectory(scripts)
