# Copyright 2013-2016 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for analyze module.
"""
import numpy as np
import pytest

from nowcast import analyze


@pytest.fixture
def linear_depths():
    return np.arange(0, 40)


@pytest.fixture
def nonuniform_depths():
    return np.array([
        0.5000003,    1.5000031,    2.50001144,    3.50003052,
        4.50007057,    5.50015068,    6.50031042,    7.50062323,
        8.50123596,    9.50243282,   10.50476551,   11.50931168,
        12.51816654,   13.53541183,   14.56898212,   15.63428783,
        16.76117325,   18.00713539,   19.48178482,   21.38997841,
        24.10025597,   28.22991562,   34.68575668,   44.51772308,
        58.48433304,   76.58558655,   98.06295776,  121.86651611,
        147.08946228,  173.11448669,  199.57304382,  226.26029968,
        253.06663513,  279.93453979,  306.834198,  333.75018311,
        360.67453003,  387.60321045,  414.53408813,  441.46609497],
        dtype=np.float32,
    )


class TestDepthAverage:
    """Unit tests for depth_average() function.
    """

    # A couple of examples of translating notebook cells into unit test
    # methods
    def test_1d_zeros_array_n_1(self, linear_depths):
        """Cell 4 case
        """
        var = np.zeros((linear_depths.shape[0], 1))
        result = analyze.depth_average(var, linear_depths, depth_axis=0)
        assert result == np.zeros((1,))
        assert result.shape == (1,)

    def test_1d_zeros_array_n(self, linear_depths):
        """Cell 5 case

        Case with var shape (40,).
        Result is not an array so should not use array equailty check.
        """
        var = np.zeros((linear_depths.shape[0]))
        result = analyze.depth_average(var, linear_depths, depth_axis=0)
        assert result == 0

    # Parametrizing a single test method with a collection of inputs
    # and expected results.
    @pytest.mark.parametrize('var, depth_axis, expected', [
        # In all cases, 40 is the length of the depth axis
        # Cell 4 case - 0 array with shape (40,1)
        (np.zeros((linear_depths().shape[0], 1)), 0, np.zeros((1,))),
        # Cell 6 case - ones array with shape (40, 1)
        (np.ones((linear_depths().shape[0], 1)), 0, np.ones((1,))),
    ])
    # Parametrization args go between self and fixture
    def test_1d_array(self, var, depth_axis, expected, linear_depths):
        result = analyze.depth_average(
            var, linear_depths, depth_axis=depth_axis)
        np.testing.assert_array_equal(result, expected)

    @pytest.mark.parametrize('var, depth_axis, expected', [
        # In all cases, 40 is the length of the depth axis
        # Cell 7 case - ones array with shape (10, 40)
        (np.ones((10, linear_depths().shape[0])), 1, np.ones((10,))),
        # Cell 8 case - ones array with shape (10, 40, 11)
        (np.ones((10, linear_depths().shape[0], 11)), 1, np.ones((10, 11))),
        # Cell 9 case - ones array with shape (1, 40, 2, 3)
        (np.ones((1, linear_depths().shape[0], 2, 3)), 1, np.ones((1, 2, 3))),
        # Cell 10 case - ones array with shape (1, 2, 40)
        (np.ones((1, 2, linear_depths().shape[0])), 2, np.ones((1, 2))),
    ])
    def test_multi_dim_array(self, var, depth_axis, expected, linear_depths):
        """Series of tests for multi-dimensional arrays
        """
        result = analyze.depth_average(
            var, linear_depths, depth_axis=depth_axis)
        np.testing.assert_array_equal(result, expected)

    def test_multi_dim_nonuniform_t(self, linear_depths):
        """Test for multidimensional array with non uniform values along the
        time axis

        Cell 11 case
        """
        ts = 3
        xs = 2
        var = np.ones((ts, linear_depths.shape[0], xs))
        var[0, ...] = 2*var[0, ...]
        expected = np.ones((ts, xs))
        expected[0, ...] = 2*expected[0, ...]
        result = analyze.depth_average(var, linear_depths, depth_axis=1)
        np.testing.assert_array_equal(result, expected)

    def test_multi_dim_nonuniform_x(self, linear_depths):
        """Test for multidimensional array with non uniform values along the
        x axis

        Cell 12 case
        """
        ts = 3
        xs = 2
        var = np.ones((ts, linear_depths.shape[0], xs))
        var[..., 1] = 2*var[..., 1]
        expected = np.ones((ts, xs))
        expected[..., 1] = 2*expected[..., 1]
        result = analyze.depth_average(var, linear_depths, depth_axis=1)
        np.testing.assert_array_equal(result, expected)

    @pytest.mark.parametrize('var, depth_axis, expected', [
        # In all cases, 40 is the length of the depth axis
        # Cell 14 case - zeros array with shape (40, 1)
        (np.zeros((nonuniform_depths().shape[0], 1)), 0, np.zeros((1,))),
        # Cell 15 case - ones array with shape (40, 1)
        (np.ones((nonuniform_depths().shape[0], 1)), 0, np.ones((1,))),
    ])
    def test_nonuniform_grid_spacing(self, var, depth_axis,
                                     expected, nonuniform_depths):
        """Series of tests for a depth array with non-uniform grid spacing.
        """
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=depth_axis)
        # using almost equal because of some floating point differences
        # Tolerance is 10^-6
        np.testing.assert_array_almost_equal(result, expected)

    @pytest.mark.parametrize('var, depth_axis, expected', [
        # In all cases, 40 is the length of the depth axis
        # Cell 19 case - masked array with shape (40,1)
        (np.zeros((nonuniform_depths().shape[0], 1)), 0, np.zeros((1,))),
        # Cell 20 case - masked array with shape (3, 40)
        (np.zeros((3, nonuniform_depths().shape[0])), 1, np.zeros((3,))),
    ])
    def test_masking_fullmask(self, var, depth_axis,
                              expected, nonuniform_depths):
        """Test for simple masked arrays - entire input array is masked.
        """
        var = np.ma.masked_values(var, 0)
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=depth_axis)
        expected = np.ma.masked_values(expected, 0)
        assert np.ma.allequal(result, expected)

    def test_masking_column_full_mask(self, nonuniform_depths):
        """Test for one column of input fully masked

        Cell 21 case
        """
        ts = 4
        var = np.ones((ts, nonuniform_depths.shape[0]))
        var[0, :] = 0
        var = np.ma.masked_values(var, 0)
        expected = np.ones((ts,))
        expected[0] = 0
        expected = np.ma.masked_values(expected, 0)
        result = analyze.depth_average(var, nonuniform_depths, depth_axis=1)
        assert np.ma.allclose(result, expected)

    def test_masking_partial_1d(self, nonuniform_depths):
        """Test for partially masked, 1d array.

        Cell 23 case
        """
        var = np.ones((nonuniform_depths.shape[0], 1))
        var[10:] = 0
        var = np.ma.masked_values(var, 0)
        expected = np.ones((1,))
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=0)
        np.testing.assert_array_almost_equal(result, expected)

    def test_masking_partial_multi(self, nonuniform_depths):
        """Test for partially masked, multidimensional array.

        Cell 24 case
        """
        ts, xs = 2, 3
        var = np.ones((ts, nonuniform_depths.shape[0], xs))
        var[0, 10:, 0] = 0
        var = np.ma.masked_values(var, 0)
        expected = np.ones((ts, xs))
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=1)
        np.testing.assert_array_almost_equal(result, expected)
