# Dependencies: spikeinterface==0.98.2, probeinterface, matplotlib, scipy

import probeinterface.plotting
from spikeinterface import extract_waveforms
from spikeinterface.extractors import read_openephys_event, read_openephys
from spikeinterface.preprocessing import phase_shift, bandpass_filter, common_reference
from spikeinterface.sorters import run_sorter
from pathlib import Path
from probeinterface.plotting import plot_probe, plot_probe_group
import matplotlib.pyplot as plt
from spikeinterface import curation
from spikeinterface.widgets import plot_timeseries
import spikeinterface as si  # TODO

# data_path = Path(r"X:\neuroinformatics\scratch\jziminski\ephys\test_data\sara\100323\2023-10-03_18-57-09\Record Node 101\experiment1")  Mounted drive on windows
data_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/sara/100323/2023-10-03_18-57-09/Record Node 101/experiment1"
)
output_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/sara/100323/derivatives"
)

show_probe = False
show_preprocessing = False

# This reads OpenEphys 'Binary' format. It determines the
# probe using probeinterface.read_openephys, which reads `settings.xml`
# and requires the NP_PROBE field is filled.
raw_recording = read_openephys(data_path)

if show_probe:
    probe = raw_recording.get_probe()
    plot_probe(probe)
    plt.show()

# Run the preprocessing steps
shifted_recording = phase_shift(raw_recording)
filtered_recording = bandpass_filter(shifted_recording, freq_min=300, freq_max=6000)
preprocessed_recording = common_reference(
    filtered_recording, reference="global", operator="median"
)

if show_preprocessing:
    # TODO: this is not working, see https://github.com/SpikeInterface/spikeinterface/issues/2099
    recs_grouped_by_shank = preprocessed_recording.split_by("group")
    for rec in recs_grouped_by_shank:
        plot_timeseries(
            preprocessed_recording,
            order_channel_by_depth=False,
            time_range=(3500, 3500),
            return_scaled=True,
            show_channel_ids=True,
            mode="map",
        )
        plt.show()

# Run the sorting
sorting = run_sorter(
    "kilosort3",
    preprocessed_recording,
    singularity_image=True,
    output_folder=(output_path / "sorting").as_posix(),
    car=False,
    freq_min=150,
)

# Curate the sorting output and extract waveforms. Calculate
# quality metrics from the waveforms.
sorting = sorting.remove_empty_units()

sorting = curation.remove_excess_spikes(sorting, preprocessed_recording)

# The way spikeinterface is setup means that quality metrics are
# calculated on the spikeinterface-preprocessed, NOT the kilosort
# preprocessed (i.e. drift-correct data).
# see https://github.com/SpikeInterface/spikeinterface/pull/1954 for details.
waveforms = extract_waveforms(
    preprocessed_recording,
    sorting,
    folder=(output_path / "postprocessing").as_posix(),
    ms_before=2,
    ms_after=2,
    max_spikes_per_unit=500,
    return_scaled=True,
    sparse=True,
    peak_sign="neg",
    method="radius",
    radius_um=75,
)

quality_metrics = si.qualitymetrics.compute_quality_metrics(waveforms)
quality_metrics.to_csv(output_path / "postprocessing")
