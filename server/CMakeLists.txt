cmake_minimum_required(VERSION 2.8)

# Install 'qraat.srv' module.
add_custom_target(qraat_srv ALL
                  COMMAND python setup.py clean --all
                  COMMAND python setup.py build
                  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})

install(CODE "execute_process(COMMAND python setup.py install 
--prefix=${CMAKE_INSTALL_PREFIX}
WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})")

# uninstall target
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
    IMMEDIATE @ONLY)

add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake)

# Descend into serv/ 
add_subdirectory(scripts)
