#include "utils/cpp_header.h"
#include "network_structures.h"


NetworkConstants::NetworkConstants() {
    N = -1; G = -1; S = -1; D = -1; }

NetworkConstants::NetworkConstants(
        int n, int g, int s, int d
)
{
    N = n; G = g; S = s; D = d;
}

TypeGroupConnection::TypeGroupConnection() {
    loc[0] = 0; loc[1] = 0; shape[0] = 0; shape[1] = 0;
};

TypeGroupConnection::TypeGroupConnection(
        int loc_0, int loc_1, int shape_0, int shape_1
)
{
    loc[0] = loc_0; loc[1] = loc_1;
    shape[0] = shape_0; shape[1] = shape_1;
}

void TypeGroupConnection::print() {
    printf("Connecting: ((%d, %d), (%d, %d))", loc[0], loc[1], shape[0], shape[1]);
}

