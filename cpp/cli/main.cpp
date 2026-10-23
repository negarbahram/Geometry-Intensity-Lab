// intensity-lab-cli: run Geometry Intensity Lab experiments without Python.
//
//   intensity-lab-cli run --settings outputs/<run>/settings.json --out DIR      re-run a saved experiment (Python or C++)
//   intensity-lab-cli run --dataset product-images --image "top/.../Pic.bmp" --out DIR [--set name=value ...]
//   intensity-lab-cli run --dataset none --image /path/to/file.png --out DIR
//   intensity-lab-cli list --dataset product-images                            list the images of a dataset
//   intensity-lab-cli summary ...same as run, but print summary.json to stdout and write nothing
//
// --set values are JSON (numbers, true/false, "strings"; a bare word is taken as a string).
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "experiment.hpp"

namespace {

int usage() {
  std::cerr << "usage:\n"
               "  intensity-lab-cli run|summary [--settings FILE] [--dataset NAME|none] [--image PATH] [--set k=v ...]"
               " [--out DIR]\n"
               "  intensity-lab-cli list --dataset NAME\n";
  return 2;
}

ilab::Json parse_value(const std::string& v) {
  try {
    return ilab::Json::parse(v);
  } catch (const std::exception&) {
    return ilab::Json(v);                // bare word, e.g. --set merge_rule=transitive
  }
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return usage();
  std::string cmd = argv[1], settings_path, dataset, image, out;
  bool have_dataset = false;
  std::vector<std::string> sets;
  for (int i = 2; i < argc; i++) {
    std::string a = argv[i];
    auto next = [&]() -> std::string {
      if (i + 1 >= argc) throw std::invalid_argument("missing value after " + a);
      return argv[++i];
    };
    try {
      if (a == "--settings") settings_path = next();
      else if (a == "--dataset") { dataset = next(); have_dataset = true; }
      else if (a == "--image") image = next();
      else if (a == "--out") out = next();
      else if (a == "--set") sets.push_back(next());
      else return usage();
    } catch (const std::exception& e) {
      std::cerr << e.what() << "\n";
      return 2;
    }
  }
  try {
    if (cmd == "list") {
      if (dataset.empty()) return usage();
      for (const auto& e : ilab::list_images(dataset)) std::cout << e.view << "\t" << e.relpath << "\n";
      return 0;
    }
    if (cmd != "run" && cmd != "summary") return usage();
    ilab::Settings s;
    if (!settings_path.empty()) {
      std::ifstream in(settings_path);
      if (!in) throw std::runtime_error("cannot read " + settings_path);
      std::stringstream ss;
      ss << in.rdbuf();
      s = ilab::Settings::from_json(ilab::Json::parse(ss.str()));
    }
    if (have_dataset) s.dataset = dataset == "none" ? "" : dataset;
    if (!image.empty()) s.image = image;
    for (const auto& kv : sets) {
      size_t eq = kv.find('=');
      if (eq == std::string::npos) throw std::invalid_argument("--set expects name=value: " + kv);
      s.set(kv.substr(0, eq), parse_value(kv.substr(eq + 1)));
    }
    if (s.image.empty()) throw std::invalid_argument("no image given");
    ilab::Result r = ilab::run(s);
    if (cmd == "summary") {
      std::cout << ilab::summary(r).dump(2) << "\n";
      return 0;
    }
    if (out.empty()) return usage();
    ilab::save(r, out);
    std::cout << out << "\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "error: " << e.what() << "\n";
    return 1;
  }
}
