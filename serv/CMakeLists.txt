INSTALL(PROGRAMS  
  rmg_env
  DESTINATION bin)

add_subdirectory(processing)
add_subdirectory(calibration)
add_subdirectory(position)
add_subdirectory(telemetry)
