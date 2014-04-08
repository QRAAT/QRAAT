INSTALL(PROGRAMS  
  rmg_env
  DESTINATION bin)

add_subdirectory(proc)
add_subdirectory(cal)
add_subdirectory(pos)
add_subdirectory(telemetry)
add_subdirectory(visualize)
