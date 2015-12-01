% if Warnings:
    STORM SURGE ADVISORY! Extreme sea levels expected for the marine areas of **${Warnings}**
% endif

Synopsis:
% if Warnings:
Strong winds over the northeast Pacific Ocean are expected to produce elevated sea levels near ${Warnings} ${PA['period']} ${PA['day']} ${PA['time']}. These elevated sea levels may present a flood risk to coastal structures and communities at high tide.
% endif

Point Atkinson
Maximum Water Level: ${PA['max_sealevel']} m
Wind speed: ${PA['windspeed']} m/s
Time: ${PA['date'].strftime('%b %d, %Y %H:%M')} [PST]

Victoria
Maximum Water Level: ${VI['max_sealevel']} m
Wind speed: ${VI['windspeed']} m/s
Time: ${VI['date'].strftime('%b %d, %Y %H:%M')} [PST]

Cherry Point
Maximum Water Level: ${CP['max_sealevel']} m
Wind speed: ${CP['windspeed']} m/s
Time: ${CP['date'].strftime('%b %d, %Y %H:%M')} [PST]

Campbell River
Maximum Water Level: ${CR['max_sealevel']} m
Wind speed: ${CR['windspeed']} m/s
Time: ${CR['date'].strftime('%b %d, %Y %H:%M')} [PST]