#include "json.hpp"

#include <cstdlib>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace ilab {

namespace {
[[noreturn]] void type_error(const char* want) { throw std::runtime_error(std::string("JSON value is not ") + want); }
}  // namespace

bool Json::as_bool() const {
  if (!is_bool()) type_error("a boolean");
  return std::get<bool>(v_);
}

int64_t Json::as_int() const {
  if (is_int()) return std::get<int64_t>(v_);
  if (is_double()) {
    double d = std::get<double>(v_);
    if (std::floor(d) == d && std::isfinite(d)) return static_cast<int64_t>(d);
  }
  type_error("an integer");
}

double Json::as_double() const {
  if (is_int()) return static_cast<double>(std::get<int64_t>(v_));
  if (is_double()) return std::get<double>(v_);
  type_error("a number");
}

const std::string& Json::as_string() const {
  if (!is_string()) type_error("a string");
  return std::get<std::string>(v_);
}

const Json::Array& Json::as_array() const {
  if (!is_array()) type_error("an array");
  return *std::get<std::shared_ptr<Array>>(v_);
}

const Json::Object& Json::as_object() const {
  if (!is_object()) type_error("an object");
  return *std::get<std::shared_ptr<Object>>(v_);
}

Json::Array& Json::arr() {
  if (!is_array()) type_error("an array");
  return *std::get<std::shared_ptr<Array>>(v_);
}

Json::Object& Json::obj() {
  if (!is_object()) type_error("an object");
  return *std::get<std::shared_ptr<Object>>(v_);
}

const Json* Json::find(const std::string& key) const {
  for (const auto& kv : as_object())
    if (kv.first == key) return &kv.second;
  return nullptr;
}

const Json& Json::at(const std::string& key) const {
  const Json* j = find(key);
  if (!j) throw std::runtime_error("missing JSON key: " + key);
  return *j;
}

Json& Json::set(const std::string& key, Json value) {
  for (auto& kv : obj())
    if (kv.first == key) return kv.second = std::move(value);
  obj().emplace_back(key, std::move(value));
  return obj().back().second;
}

std::string py_float(double d) {
  if (std::isnan(d)) return "NaN";
  if (std::isinf(d)) return d > 0 ? "Infinity" : "-Infinity";
  if (d == 0) return std::signbit(d) ? "-0.0" : "0.0";
  // Shortest scientific representation that round-trips, then Python repr's layout rules:
  // fixed notation for decimal exponents -4..15, otherwise d.ddde+XX.
  char buf[64];
  int prec = 0;
  for (prec = 0; prec < 17; prec++) {
    std::snprintf(buf, sizeof buf, "%.*e", prec, d);
    if (std::strtod(buf, nullptr) == d) break;
  }
  std::string s(buf);
  bool neg = s[0] == '-';
  if (neg) s.erase(0, 1);
  size_t e = s.find('e');
  int exp10 = std::atoi(s.c_str() + e + 1);
  std::string digits;
  for (size_t i = 0; i < e; i++)
    if (s[i] != '.') digits += s[i];
  while (digits.size() > 1 && digits.back() == '0') digits.pop_back();
  std::string out;
  if (exp10 >= -4 && exp10 < 16) {
    if (exp10 >= 0) {
      std::string ip = digits.substr(0, std::min<size_t>(digits.size(), exp10 + 1));
      ip.append(exp10 + 1 > static_cast<int>(digits.size()) ? exp10 + 1 - digits.size() : 0, '0');
      std::string fp = static_cast<int>(digits.size()) > exp10 + 1 ? digits.substr(exp10 + 1) : "0";
      out = ip + "." + fp;
    } else {
      out = "0." + std::string(-exp10 - 1, '0') + digits;
    }
  } else {
    out = digits.substr(0, 1);
    if (digits.size() > 1) out += "." + digits.substr(1);
    char ex[16];
    std::snprintf(ex, sizeof ex, "e%c%02d", exp10 < 0 ? '-' : '+', std::abs(exp10));
    out += ex;
  }
  return (neg ? "-" : "") + out;
}

namespace {

void write_string(std::string& out, const std::string& s) {
  out += '"';
  for (unsigned char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char b[8];
          std::snprintf(b, sizeof b, "\\u%04x", c);
          out += b;
        } else {
          out += static_cast<char>(c);
        }
    }
  }
  out += '"';
}

}  // namespace

void Json::write(std::string& out, int indent, int depth) const {
  auto newline = [&](int d) {
    if (indent <= 0) return;
    out += '\n';
    out.append(static_cast<size_t>(indent * d), ' ');
  };
  if (is_null()) out += "null";
  else if (is_bool()) out += std::get<bool>(v_) ? "true" : "false";
  else if (is_int()) out += std::to_string(std::get<int64_t>(v_));
  else if (is_double()) out += py_float(std::get<double>(v_));
  else if (is_string()) write_string(out, std::get<std::string>(v_));
  else if (is_array()) {
    const auto& a = as_array();
    if (a.empty()) { out += "[]"; return; }
    out += '[';
    for (size_t i = 0; i < a.size(); i++) {
      if (i) out += indent > 0 ? "," : ", ";
      newline(depth + 1);
      a[i].write(out, indent, depth + 1);
    }
    newline(depth);
    out += ']';
  } else {
    const auto& o = as_object();
    if (o.empty()) { out += "{}"; return; }
    out += '{';
    for (size_t i = 0; i < o.size(); i++) {
      if (i) out += indent > 0 ? "," : ", ";
      newline(depth + 1);
      write_string(out, o[i].first);
      out += ": ";
      o[i].second.write(out, indent, depth + 1);
    }
    newline(depth);
    out += '}';
  }
}

std::string Json::dump(int indent) const {
  std::string out;
  write(out, indent, 0);
  return out;
}

namespace {

struct Parser {
  const std::string& s;
  size_t i = 0;

  [[noreturn]] void fail(const std::string& what) {
    throw std::runtime_error("invalid JSON at offset " + std::to_string(i) + ": " + what);
  }
  void ws() {
    while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++;
  }
  bool lit(const char* t) {
    size_t n = std::strlen(t);
    if (s.compare(i, n, t) == 0) { i += n; return true; }
    return false;
  }
  std::string str() {
    if (s[i] != '"') fail("expected string");
    i++;
    std::string out;
    while (i < s.size() && s[i] != '"') {
      char c = s[i++];
      if (c != '\\') { out += c; continue; }
      if (i >= s.size()) fail("bad escape");
      char e = s[i++];
      switch (e) {
        case '"': out += '"'; break;
        case '\\': out += '\\'; break;
        case '/': out += '/'; break;
        case 'b': out += '\b'; break;
        case 'f': out += '\f'; break;
        case 'n': out += '\n'; break;
        case 'r': out += '\r'; break;
        case 't': out += '\t'; break;
        case 'u': {
          if (i + 4 > s.size()) fail("bad \\u escape");
          unsigned cp = std::stoul(s.substr(i, 4), nullptr, 16);
          i += 4;
          if (cp >= 0xD800 && cp <= 0xDBFF && s.compare(i, 2, "\\u") == 0) {
            unsigned lo = std::stoul(s.substr(i + 2, 4), nullptr, 16);
            i += 6;
            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
          }
          if (cp < 0x80) out += static_cast<char>(cp);
          else if (cp < 0x800) { out += static_cast<char>(0xC0 | (cp >> 6)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
          else if (cp < 0x10000) {
            out += static_cast<char>(0xE0 | (cp >> 12));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
          } else {
            out += static_cast<char>(0xF0 | (cp >> 18));
            out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
          }
          break;
        }
        default: fail("bad escape");
      }
    }
    if (i >= s.size()) fail("unterminated string");
    i++;
    return out;
  }
  Json value() {
    ws();
    if (i >= s.size()) fail("unexpected end");
    char c = s[i];
    if (c == '{') {
      i++;
      Json o = Json::object();
      ws();
      if (s[i] == '}') { i++; return o; }
      while (true) {
        ws();
        std::string k = str();
        ws();
        if (s[i] != ':') fail("expected ':'");
        i++;
        o.obj().emplace_back(k, value());
        ws();
        if (s[i] == ',') { i++; continue; }
        if (s[i] == '}') { i++; return o; }
        fail("expected ',' or '}'");
      }
    }
    if (c == '[') {
      i++;
      Json a = Json::array();
      ws();
      if (s[i] == ']') { i++; return a; }
      while (true) {
        a.push(value());
        ws();
        if (s[i] == ',') { i++; continue; }
        if (s[i] == ']') { i++; return a; }
        fail("expected ',' or ']'");
      }
    }
    if (c == '"') return Json(str());
    if (lit("true")) return Json(true);
    if (lit("false")) return Json(false);
    if (lit("null")) return Json(nullptr);
    if (lit("NaN")) return Json(std::nan(""));
    if (lit("Infinity")) return Json(HUGE_VAL);
    if (lit("-Infinity")) return Json(-HUGE_VAL);
    size_t start = i;
    if (s[i] == '-') i++;
    bool integral = true;
    while (i < s.size() && (std::isdigit(static_cast<unsigned char>(s[i])) || s[i] == '.' || s[i] == 'e' ||
                            s[i] == 'E' || s[i] == '+' || s[i] == '-')) {
      if (s[i] == '.' || s[i] == 'e' || s[i] == 'E') integral = false;
      i++;
    }
    std::string num = s.substr(start, i - start);
    if (num.empty() || num == "-") fail("unexpected character");
    if (integral) return Json(static_cast<long long>(std::stoll(num)));
    return Json(std::stod(num));
  }
};

}  // namespace

Json Json::parse(const std::string& text) {
  Parser p{text};
  Json v = p.value();
  p.ws();
  if (p.i != text.size()) p.fail("trailing characters");
  return v;
}

}  // namespace ilab
