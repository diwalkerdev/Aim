#include "calculator.h"
#include <cassert>
#include <stdio.h>

void test_calculator() {
  auto result = add(1, 1);
  assert(result > 1.999 && result < 2.111);
}

int main() {
  test_calculator();
  printf("Calculator Tests Complete.\n");
  return 0;
}
