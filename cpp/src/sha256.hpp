#pragma once
#include <string>

namespace ilab {

/** Lower-case hex SHA-256 of a file's bytes (identity of the processed image, as in the Python summary). */
std::string sha256_file(const std::string& path);

}  // namespace ilab
