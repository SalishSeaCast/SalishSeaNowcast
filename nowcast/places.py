# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Salish Sea NEMO nowcast places information.
"""
PLACES = {
    # Tide gauge stations
    'Point Atkinson': {
        'lat_lon': (49.33, -123.25),  # deg N, deg E
        'stn number': 7795,  # Canadian Hydrographic Service (CHS)
        'mean sea level': 3.09,  # m above chart datum
        'historical max sea level': 5.61,  # m above chart datum
    },
}
