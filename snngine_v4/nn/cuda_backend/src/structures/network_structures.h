#pragma once

struct NetworkConstants
{
    int N; int G; int S; int D;
    NetworkConstants();
    NetworkConstants(int n, int g, int s, int d);
} ;

struct TypeGroupConnection
{
    int loc[2]{};
    int shape[2]{};

    TypeGroupConnection();

    TypeGroupConnection(int loc_0, int loc_1,
                        int shape_0, int shape_1);

    void print();

} ;