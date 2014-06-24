add_library(rmg-pulse SHARED
  pulse_data.cc
)

set_target_properties(rmg-pulse PROPERTIES DEFINE_SYMBOL "gnuradio_rmg_pulse_EXPORTS")

install(TARGETS rmg-pulse
    LIBRARY DESTINATION lib${LIB_SUFFIX} # .so/.dylib file
    ARCHIVE DESTINATION lib${LIB_SUFFIX} # .lib file
    RUNTIME DESTINATION bin              # .dll file
)
