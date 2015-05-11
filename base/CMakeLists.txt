cmake_minimum_required(VERSION 2.8)

#make sure our local CMake Modules path comes first
list(INSERT CMAKE_MODULE_PATH 0 ${CMAKE_SOURCE_DIR}/cmake/Modules)

########################################################################
# Setup the include and linker paths
########################################################################
include_directories(
    ${CMAKE_SOURCE_DIR}/lib
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/lib
    ${CMAKE_BINARY_DIR}/include
)

########################################################################
# Create uninstall target
########################################################################
#configure_file(
#    ${CMAKE_SOURCE_DIR}/cmake/cmake_uninstall.cmake.in
#    ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
#@ONLY)

#add_custom_target(uninstall
#    ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
#)

########################################################################
# Add subdirectories
########################################################################
add_subdirectory(include)
add_subdirectory(lib)
add_subdirectory(python)
add_subdirectory(scripts)
