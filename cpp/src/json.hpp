// Minimal ordered JSON value with a reader and a writer. Enough for settings files and result summaries; object keys
// keep insertion order so written files read like the Python reference output.
#pragma once
#include <cstdint>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace ilab {

class Json {
 public:
  using Array = std::vector<Json>;
  using Object = std::vector<std::pair<std::string, Json>>;

  Json() : v_(nullptr) {}
  Json(std::nullptr_t) : v_(nullptr) {}
  Json(bool b) : v_(b) {}
  Json(int i) : v_(static_cast<int64_t>(i)) {}
  Json(long i) : v_(static_cast<int64_t>(i)) {}
  Json(long long i) : v_(static_cast<int64_t>(i)) {}
  Json(unsigned i) : v_(static_cast<int64_t>(i)) {}
  Json(unsigned long i) : v_(static_cast<int64_t>(i)) {}
  Json(unsigned long long i) : v_(static_cast<int64_t>(i)) {}
  Json(double d) : v_(d) {}
  Json(const char* s) : v_(std::string(s)) {}
  Json(std::string s) : v_(std::move(s)) {}
  Json(Array a) : v_(std::make_shared<Array>(std::move(a))) {}
  Json(Object o) : v_(std::make_shared<Object>(std::move(o))) {}

  static Json array() { return Json(Array{}); }
  static Json object() { return Json(Object{}); }
  template <class T>
  static Json from(const std::vector<T>& v) {
    Array a;
    for (const auto& x : v) a.emplace_back(x);
    return Json(std::move(a));
  }

  bool is_null() const { return std::holds_alternative<std::nullptr_t>(v_); }
  bool is_bool() const { return std::holds_alternative<bool>(v_); }
  bool is_int() const { return std::holds_alternative<int64_t>(v_); }
  bool is_double() const { return std::holds_alternative<double>(v_); }
  bool is_number() const { return is_int() || is_double(); }
  bool is_string() const { return std::holds_alternative<std::string>(v_); }
  bool is_array() const { return std::holds_alternative<std::shared_ptr<Array>>(v_); }
  bool is_object() const { return std::holds_alternative<std::shared_ptr<Object>>(v_); }

  bool as_bool() const;
  int64_t as_int() const;        // accepts an integral double (1.0), like Python's int fields fed from JSON
  double as_double() const;
  const std::string& as_string() const;
  const Array& as_array() const;
  const Object& as_object() const;
  Array& arr();
  Object& obj();

  /** Object member access; `at` throws when missing, `find` returns nullptr. */
  const Json& at(const std::string& key) const;
  const Json* find(const std::string& key) const;
  /** Set (or replace) a member of an object, keeping its position when it already exists. */
  Json& set(const std::string& key, Json value);
  void push(Json value) { arr().push_back(std::move(value)); }

  std::string dump(int indent = 2) const;
  static Json parse(const std::string& text);

 private:
  void write(std::string& out, int indent, int depth) const;
  std::variant<std::nullptr_t, bool, int64_t, double, std::string, std::shared_ptr<Array>, std::shared_ptr<Object>> v_;
};

/** Python's repr() of a float: shortest round-trip digits, always with a '.', 'e', "inf" or "nan". */
std::string py_float(double d);

}  // namespace ilab
