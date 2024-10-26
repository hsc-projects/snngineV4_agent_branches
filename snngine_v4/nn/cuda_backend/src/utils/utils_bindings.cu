#include <include/pybind11/include/pybind11/pybind11.h>
#include <include/pybind11/include/pybind11/numpy.h>
#include <include/pybind11/include/pybind11/stl.h>

namespace py = pybind11;

#include "utils/curand_states.cuh"


PYBIND11_MODULE(snn_utils, m)
{

    py::class_<CuRandStates, std::shared_ptr<CuRandStates>>(m, "CuRandStates_")
            .def(py::init<int>())
            .def_readonly("n_states", &CuRandStates::n_states)
            .def_readonly("states", &CuRandStates::states)
            .def("__repr__",
                 [](const CuRandStates &cs) {
                     return "CuRandStates_(" + std::to_string(cs.n_states) + ")";
                 }
            );

    py::class_<CuRandStatesPointer>(m, "CuRandStates")
            .def(py::init<int>())
            .def_property_readonly("n_states", &CuRandStatesPointer::n_states)
            .def("ptr", &CuRandStatesPointer::ptr)
            .def("__repr__",
                 [](const CuRandStatesPointer &cs) {
                     return "CuRandStates(" + std::to_string(cs.ptr_->n_states) + ")";
                 }
            );
}

