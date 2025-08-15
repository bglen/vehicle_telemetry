import sys
import numpy as np
import rerun as rr
import rerun.blueprint as rrb
from PyQt6.QtWidgets import QApplication, QFileDialog

rr.init("Glen Racing Telemetry", spawn=True)

# Load data
# Use Qt file dialog to select CSV file
app = QApplication(sys.argv)
csv_path, _ = QFileDialog.getOpenFileName(
    None,
    "Select CSV Data File",
    "",
    "CSV Files (*.csv);;All Files (*)"
)
if not csv_path:
    sys.exit("No file selected, exiting...")

data = np.genfromtxt(csv_path, delimiter=",", names=True)

# Load video data
video_path = "test_video.mp4"

# Aquire the timeline for the data
timestamps = data["timestamp"]
time = rr.TimeColumn("timestamp", duration=timestamps)

# Create point data for the GG diagram
positions = np.column_stack((data["AY1"], data["AX1"]))
n = positions.shape[0]
colors = np.tile([255, 0, 0], (n, 1)).astype(int)
radii = np.full(n, 0.01)


# Create the GG Diagram
rr.set_time("timestamp", duration=0)

# Axis Lines
rr.log(
    "imu/gg/arrows",
    rr.Arrows2D(
        origins=[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        vectors=[[2.1, 0.0], [-2.1, 0.0], [0.0, 2.1], [0.0, -2.1]],
        colors=[[185, 185, 185]],
        labels=["left turn", "right turn", "acceleration", "braking"],
        radii=0.005,
    ),
)

# Concentric circles at 0.5G increments
segments = 50 # higher = smoother
circle_radii = [0.5, 1.0, 1.5, 2.0]
for r in circle_radii:
    theta = np.linspace(0, 2*np.pi, segments, endpoint=True)
    pts = np.column_stack([
        r * np.cos(theta),
        r * np.sin(theta)
    ])
    # rr.LineStripes2D takes a (N×2) array of points and will draw a closed loop
    rr.log(f"imu/gg/r={r:.2f}", rr.LineStrips2D(pts, radii=0.005, colors=[[60, 60, 60]]))

rr.log("imu/gg", rr.Points2D(positions, colors=colors, radii=radii))

# Log scalar time series data
rr.send_columns(
    "imu/ax",
    indexes=[time],
    columns=rr.Scalars.columns(scalars=data["AX1"]),
    )

rr.send_columns(
    "imu/ay",
    indexes=[time],
    columns=rr.Scalars.columns(scalars=data["AY1"]),
    )

rr.send_columns(
    "imu/az",
    indexes=[time],
    columns=rr.Scalars.columns(scalars=data["AZ"]),
    )

rr.send_columns(
    "imu/yaw_rate",
    indexes=[time],
    columns=rr.Scalars.columns(scalars=data["PSIP1"]),
    )

rr.send_columns(
    "imu/roll_rate",
    indexes=[time],
    columns=rr.Scalars.columns(scalars=data["PSIP3"]),
    )

# Log video asset which is referred to by frame references.
video_asset = rr.AssetVideo(path=video_path, media_type="video/mp4")
rr.log("video", video_asset, static=True)

# Send automatically determined video frame timestamps.
frame_timestamps_ns = video_asset.read_frame_timestamps_nanos()
rr.send_columns(
    "video",
    # Note timeline values don't have to be the same as the video timestamps.
    indexes=[rr.TimeColumn("video_time", duration=1e-9 * frame_timestamps_ns)],
    columns=rr.VideoFrameReference.columns_nanos(frame_timestamps_ns),
)

# Create a Spatial2D view to display the points.
blueprint = rrb.Blueprint(
    rrb.Horizontal(
        rrb.Vertical(
            # Time Series view for the sensor data
            rrb.TimeSeriesView(
                origin="imu/yaw_rate",
                name="Yaw Rate ",
            ),
            rrb.TimeSeriesView(
                origin="imu/roll_rate",
                name="Roll Rate",
            ),
        ),
        rrb.Vertical(
            # Time Series view for the sensor data
            rrb.TimeSeriesView(
                origin="imu/ax",
                name="Longitudinal Acceleration (G)",
            ),
            rrb.TimeSeriesView(
                origin="imu/ay",
                name="Lateral Acceleration (G)",
            ),
            rrb.TimeSeriesView(
                origin="imu/az",
                name="Vertical Acceleration (G)",
            ),
        ),
        rrb.Vertical(
            rrb.Spatial2DView(
                origin="imu/gg",
                name="GG Diagram",
                visual_bounds=rrb.VisualBounds2D(x_range=[-2, 2], y_range=[-2, 2]),
            ),
            rrb.Spatial2DView(
                origin="video",
                name="Video",
            ),
        ),
        
    ),
    #collapse_panels=True
)

rr.send_blueprint(blueprint)