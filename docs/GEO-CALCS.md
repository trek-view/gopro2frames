## gps_time_seconds_next

Is time to next photo.

Uses GPSDateTime values (to subsecond resolution) from each photo. Calculation is:

`Photo Next GPSDateTime - Photo Current GPSDateTime`

Output in seconds

## gps_distance_meters_next

Is distance to next photo lat/lon.

To calculate distance, you can use the [Haversine formula](https://en.wikipedia.org/wiki/Haversine_formula) to find the distance between two points on a sphere (Earth) given their longitudes and latitudes.

Output is meters

![](/docs/distance.png)

## gps_elevation_change_meters_next

Is elevation change to next photo.

Uses elevation values from each photo. Calculation is:

`Photo Next Elevation - Photo Elevation`

Output in meters.

## gps_pitch_degrees_next

Is pitch (or angle) to next photo.

pitch(θ) = tan(θ) = opposite / adjacent

We have the adjacent measurement (gps_distance_meters_next), and the opposite value (gps_elevation_change_meters_next).

Occasionally GPS lat/lon in points is identical, but elevation might change. In this case we default to write pitch as 0. This only happens if distance = 0.

Output is in degrees between -90 and 90

![](/docs/pitch.png)

## gps_speed_meters_second_next

Is speed to next photo. 

Speed = distance / time

We have both these values from above (`gps_distance_meters_next` and `gps_time_seconds_next`)

Output is meters per second.

## gps_velocity_east_meters_second_next

Is velocity (east vector) to next photo.

Velocity = Displacement / Time in a direction.

So Velocity East = (distance photo A to point C) / Time (gps_time_seconds_next)

Note, this calculation can result in a negative output. North and East are positive directions. If you travel West/South, in terms of an East/North vector, you will be traveling in both a negative East/North velocity.

If I drive from home to work (defining my positive direction), then my velocity is positive if I go to work, but negative when I go home from work. It is all about direction seen from how I defined my positive axis.

![](/docs/velocity-east-north.jpeg)

![](/docs/velocity-east-north-negative-example.jpeg)

Output is meters per second (can be negative)

## gps_velocity_north_meters_second_next

Is velocity (north vector) to next photo.

Same as above, but...

Velocity North = (distance point C to photo B) / Time (gps_time_seconds_next)

Output is meters per second (can be negative)

## gps_velocity_up_meters_second_next

Is velocity (up/vertical) to next photo.

Same as above, but...

Velocity Up = (gps_elevation_change_meters_next) / Time (gps_time_seconds_next)

Output is meters per second (can be negative)

## gps_heading_degrees_next

Is heading (from North) to next photo.

![](/docs/heading.png)

Output is degrees between 0-360.