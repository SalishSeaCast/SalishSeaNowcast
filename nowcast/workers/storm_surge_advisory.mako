<%doc>
   Copyright 2013 – present by the SalishSeaCast Project contributors
   and The University of British Columbia

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


   Template for storm surge advisory feed entry.
</%doc>
**STORM SURGE ADVISORY**

${'Extreme' if 'extreme' in conditions[tide_gauge_stn]['risk_level'] else 'Elevated'}
sea levels expected for the marine areas of ${city}

**Synopsis**:
Strong winds over the northeast Pacific Ocean are expected
to produce elevated sea levels near ${city}
${conditions[tide_gauge_stn]['humanized_max_ssh_time']}.
These elevated sea levels may present a flood risk to
coastal structures and communities at high tide.

${tide_gauge_stn_info(tide_gauge_stn, conditions)}

Wind speed and direction are averages over the 4 hours preceding
the maximum water level to give information regarding wave setup
that may augment flood risks.

<%def name="tide_gauge_stn_info(stn, conditions)">
**${stn}**

**Risk Level:** ${conditions[stn]['risk_level'].title()}

**Maximum Water Level:** ${round(conditions[stn]['max_ssh_msl'], 1)} m
above chart datum

**Wind:** ${int(round(conditions[stn]['wind_speed_4h_avg_kph'], 0))} km/hr
(${int(round(conditions[stn]['wind_speed_4h_avg_knots'], 0))} knots)
from the ${conditions[stn]['wind_dir_4h_avg_heading']}
(${int(round(conditions[stn]['wind_dir_4h_avg_bearing'], 0))}°)

**Time of Maximum Water Level:**
${conditions[stn]['max_ssh_time'].format('ddd MMM DD, YYYY HH:mm')}
[${conditions[stn]['max_ssh_time_tzname']}]
</%def>
