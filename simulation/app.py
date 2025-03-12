# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import yaml
import numpy as np
from simulation import Simulation

plt.rcParams.update({
    'axes.titlesize': 32,     # Title font size
    'axes.labelsize': 32,     # Axis label font size
    'xtick.labelsize': 32,    # X-axis tick label font size
    'ytick.labelsize': 32,    # Y-axis tick label font size
    'legend.fontsize': 32,    # Legend font size
    'font.size': 32           # Base font size
})

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

defaults = config.get('defaults', {})
beam_current_default = defaults.get('beam_current', 2e-9)
radiation_coeff_default = defaults.get('radiation_coeff', 0.0001)
time_step_default = defaults.get('time_step', 1.0)
beam_area_default = defaults.get('beam_area', 1.0)
microwave_frequency_default = defaults.get('microwave_frequency', 140.1)

st.title("Interactive Polarization Simulation")

st.sidebar.header("Simulation Controls")


beam_current = st.sidebar.number_input("Beam Current (A)",
                                       min_value=1e-9, max_value=1e-3,
                                       value=beam_current_default,
                                       step=1e-9, format="%.1e")
alpha = st.sidebar.number_input("dose decay",
                                          min_value=1e-6, max_value=1e-2,
                                          value=radiation_coeff_default,
                                          format="%.5f")
time_step = st.sidebar.slider("Time Step (seconds)",
                              0.1, 10.0, time_step_default, 0.1)
beam_area = st.sidebar.number_input("Beam Area (cm²)",
                                    min_value=0.1, max_value=10.0,
                                    value=beam_area_default,
                                    step=0.1)

if "running" not in st.session_state:
    st.session_state.running = False

if "sim" not in st.session_state:
    st.session_state.sim = Simulation(
    beam_current=beam_current,
    time_step=time_step,
    beam_area=beam_area,
    microwave_frequency=microwave_frequency_default,
    pmax=0.95,  # or from your config
    phi=25.6,   # or from your config
    trip_rate_per_hour=12,
    trip_duration_min=(20, 300),
)

# Initialize arrays in session state for history
if "time_array" not in st.session_state:
    st.session_state.time_array = []
    st.session_state.pol_array = []
    st.session_state.freq_array = []
    st.session_state.dose_array = []

if "beam_current_array" not in st.session_state:
    st.session_state.beam_current_array = []


# Buttons for microwave frequency adjustments
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Increase Frequency"):
        st.session_state.sim.microwave_frequency += 0.001
with col2:
    if st.button("Decrease Frequency"):
        st.session_state.sim.microwave_frequency -= 0.001

# Start/Stop simulation buttons
col3, col4 = st.columns([1, 1])
with col3:
    if st.button("Start Simulation"):
        st.session_state.running = True
with col4:
    if st.button("Stop Simulation"):
        st.session_state.running = False

st.write(f"### Current Microwave Frequency: {st.session_state.sim.microwave_frequency:.1f} GHz")

# Create containers for the plots (3 rows, single column)
polarization_plot = st.empty()
frequency_plot = st.empty()
dose_plot = st.empty()
current_plot = st.empty()

while st.session_state.running:
    state = st.session_state.sim.step()
    st.session_state.time_array.append(state["time"])
    st.session_state.pol_array.append(state["polarization"])
    st.session_state.freq_array.append(state["microwave_frequency"])
    st.session_state.dose_array.append(state["accumulated_dose"])
    st.session_state.beam_current_array.append(state["beam_current"])

    # Plot Polarization
    fig1, ax1 = plt.subplots(figsize=(24, 6))
    ax1.scatter(st.session_state.time_array, st.session_state.pol_array, color="blue")
    ax1.set_title("Polarization Over Time")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Polarization")
    ax1.grid(True)
    polarization_plot.pyplot(fig1)
    plt.close(fig1)

    # Plot Microwave Frequency
    fig2, ax2 = plt.subplots(figsize=(24, 6))
    ax2.scatter(st.session_state.time_array, st.session_state.freq_array, color="purple")
    ax2.set_title("Microwave Frequency Over Time")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Frequency (GHz)")
    ax2.grid(True)
    frequency_plot.pyplot(fig2)
    plt.close(fig2)

    # Plot Accumulated Dose
    fig3, ax3 = plt.subplots(figsize=(24, 6))
    ax3.scatter(st.session_state.time_array, st.session_state.dose_array, color="green")
    ax3.set_title("Accumulated Dose Over Time")
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Accumulated Dose (e-/cm²)")
    ax3.grid(True)
    dose_plot.pyplot(fig3)
    plt.close(fig3)
    
        # Beam Current Plot
    fig4, ax4 = plt.subplots(figsize=(24, 6))
    ax4.scatter(st.session_state.time_array, st.session_state.beam_current_array, color="red")
    ax4.set_title("Beam Current Over Time")
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Beam Current (A)")
    ax4.grid(True)
    current_plot.pyplot(fig4)
    plt.close(fig4)

    time.sleep(time_step)
