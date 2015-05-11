INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_RMG rmg)

FIND_PATH(
    RMG_INCLUDE_DIRS
    NAMES rmg/api.h
    HINTS $ENV{RMG_DIR}/include
        ${PC_RMG_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    RMG_LIBRARIES
    NAMES gnuradio-rmg
    HINTS $ENV{RMG_DIR}/lib
        ${PC_RMG_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(RMG DEFAULT_MSG RMG_LIBRARIES RMG_INCLUDE_DIRS)
MARK_AS_ADVANCED(RMG_LIBRARIES RMG_INCLUDE_DIRS)

