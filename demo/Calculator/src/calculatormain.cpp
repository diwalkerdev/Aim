#include "calculator.h"
#include <stdio.h>

int main()
{
    int x = 41;
    int y = 1;

    auto result = add(x, y);

    printf("%d + %d = %d\n", x, y, result);

    return 0;
}
