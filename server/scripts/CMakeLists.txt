INSTALL(PROGRAMS  
  rmg_dbcheck
  DESTINATION bin)

add_subdirectory(proc)
add_subdirectory(cal)
add_subdirectory(pos)
add_subdirectory(track)
add_subdirectory(filter)
add_subdirectory(telemetry)
add_subdirectory(visualize)
add_subdirectory(gps_afsk)
