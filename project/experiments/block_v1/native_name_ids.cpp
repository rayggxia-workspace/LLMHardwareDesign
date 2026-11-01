// Read-only access to the installed Naja name interner for diagnostics.
#include "NLName.h"
#include <cstdint>
#include <string>
extern "C" std::uint32_t bv1_name_id(const char* name) {
  return naja::NL::NLName(std::string(name)).getID();
}
