"""Unit tests for bathy_tools.
"""
from __future__ import division
"""
Copyright 2013-2015 The Salish Sea MEOPAR contributors
and The University of British Columbia

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import numpy as np
import netCDF4 as nc
import os
import pytest

from nowcast import analyze


@pytest.fixture
def linear_depths():
    return np.arange(0, 40)


# @pytest.fixture
# def nonuniform_depths():
#     # Don't like that these tests depend on the existence of this file
#     base = '/data/dlatorne/MEOPAR/SalishSea/nowcast/01oct15'
#     path = os.path.join(base, 'SalishSea_1d_20151001_20151001_grid_T.nc')
#     f = nc.Dataset(path, 'r')
#     return f.variables['deptht'][:]


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
        # Case with var shape (40,). Result is not an array so should not use
        # array equailty check
        """Cell 5 case
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
        """Series of tests for multi-dimensional arrays"""
        result = analyze.depth_average(
            var, linear_depths, depth_axis=depth_axis)
        np.testing.assert_array_equal(result, expected)

    def test_multi_dim_nonuniform_t(self, linear_depths):
        # Cell 11 case
        """Test for multidimensional array with non uniform values along the
        time axis"""
        ts = 3
        xs = 2
        var = np.ones((ts, linear_depths.shape[0], xs))
        var[0, ...] = 2*var[0, ...]
        expected = np.ones((ts, xs))
        expected[0, ...] = 2*expected[0, ...]
        result = analyze.depth_average(var, linear_depths, depth_axis=1)
        np.testing.assert_array_equal(result, expected)

    def test_multi_dim_nonuniform_x(self, linear_depths):
        # Cell 12 case
        """Test for multidimensional array with non uniform values along the
        x axis"""
        ts = 3
        xs = 2
        var = np.ones((ts, linear_depths.shape[0], xs))
        var[..., 1] = 2*var[..., 1]
        expected = np.ones((ts, xs))
        expected[..., 1] = 2*expected[..., 1]
        result = analyze.depth_average(var, linear_depths, depth_axis=1)
        np.testing.assert_array_equal(result, expected)

    @pytest.mark.xfail
    # @pytest.mark.parametrize('var, depth_axis, expected', [
    #     # In all cases, 40 is the length of the depth axis
    #     # Cell 14 case - zeros array with shape (40, 1)
    #     (np.zeros((nonuniform_depths().shape[0], 1)), 0, np.zeros((1,))),
    #     # Cell 15 case - ones array with shape (40, 1)
    #     (np.ones((nonuniform_depths().shape[0], 1)), 0, np.ones((1,))),
    # ])
    def test_nonuniform_grid_spacing(self, var, depth_axis,
                                     expected, nonuniform_depths):
        """Series of tests for a depth array with non-uniform grid spacing."""
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=depth_axis)
        # using almost equal because of some floating point differences
        # Tolerance is 10^-6
        np.testing.assert_array_almost_equal(result, expected)

    @pytest.mark.xfail
    # @pytest.mark.parametrize('var, depth_axis, expected', [
    #     # In all cases, 40 is the length of the depth axis
    #     # Cell 19 case - masked array with shape (40,1)
    #     (np.zeros((nonuniform_depths().shape[0], 1)), 0, np.zeros((1,))),
    #     # Cell 20 case - masked array with shape (3, 40)
    #     (np.zeros((3, nonuniform_depths().shape[0])), 1, np.zeros((3,))),
    # ])
    def test_masking_fullmask(self, var, depth_axis,
                              expected, nonuniform_depths):
        """Test for simple masked arrays - entire input array is masked."""
        var = np.ma.masked_values(var, 0)
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=depth_axis)
        expected = np.ma.masked_values(expected, 0)
        assert np.ma.allequal(result, expected)

    @pytest.mark.xfail
    def test_masking_column_full_mask(self, nonuniform_depths):
        """Test for one column of input fully masked"""
        # Cell 21 case
        ts = 4
        var = np.ones((ts,nonuniform_depths.shape[0]))
        var[0,:]=0
        var=np.ma.masked_values(var,0)
        expected = np.ones((ts,))
        expected[0] = 0
        expected = np.ma.masked_values(expected, 0)
        result = analyze.depth_average(var,nonuniform_depths,depth_axis=1)
        assert np.ma.allclose(result, expected)


    @pytest.mark.xfail
    def test_masking_partial_1d(self, nonuniform_depths):
        # Cell 23 case
        """Test for partially masked, 1d array."""
        var = np.ones((nonuniform_depths.shape[0], 1))
        var[10:] = 0
        var=np.ma.masked_values(var, 0)
        expected = np.ones((1,))
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=0)
        np.testing.assert_array_almost_equal(result, expected)

    @pytest.mark.xfail
    def test_masking_partial_multi(self, nonuniform_depths):
        # Cell 24 case
        """Test for partially masked, multidimensional array."""
        ts=2
        xs=3
        var = np.ones((ts, nonuniform_depths.shape[0], xs))
        var[0, 10:, 0] = 0
        var=np.ma.masked_values(var,0)
        expected = np.ones((ts, xs))
        result = analyze.depth_average(
            var, nonuniform_depths, depth_axis=1)
        np.testing.assert_array_almost_equal(result, expected)
