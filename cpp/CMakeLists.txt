cmake_minimum_required(VERSION 3.16)
project(intensity_lab_cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# OpenCV 4.11 (core, imgproc, imgcodecs), built by scripts/build_opencv.sh into third_party/opencv-install,
# or pass -DOpenCV_DIR=<another install>.
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/third_party/opencv-install")
find_package(OpenCV 4 REQUIRED COMPONENTS core imgproc imgcodecs)

add_library(intensity_core STATIC
  src/json.cpp src/sha256.cpp src/histogram.cpp src/imageio.cpp src/gmm.cpp src/minima.cpp
  src/regions.cpp src/boundaries.cpp src/experiment.cpp)
target_include_directories(intensity_core PUBLIC src)
target_link_libraries(intensity_core PUBLIC ${OpenCV_LIBS})
target_compile_options(intensity_core PRIVATE -Wall -Wextra -Wno-unused-parameter)
# Strict IEEE arithmetic: no fused multiply-add contraction, so sums and products round like NumPy's.
target_compile_options(intensity_core PRIVATE -ffp-contract=off)
target_compile_definitions(intensity_core PRIVATE ILAB_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/..")

add_executable(intensity-lab-cli cli/main.cpp)
target_link_libraries(intensity-lab-cli PRIVATE intensity_core)

enable_testing()
add_executable(intensity-core-tests tests/test_core.cpp)
target_link_libraries(intensity-core-tests PRIVATE intensity_core)
target_compile_definitions(intensity-core-tests PRIVATE ILAB_EXAMPLES="${CMAKE_CURRENT_SOURCE_DIR}/../examples")
add_test(NAME core COMMAND intensity-core-tests)
