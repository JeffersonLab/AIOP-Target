# simulation.py
import math
import random

ELECTRON_CHARGE = 1.602e-19

def single_exponential_polarization(dose, pmax, phi):
    """
    dose: accumulated dose (e-/cm²)
    pmax: maximum polarization (fraction)
    phi: single-exponential decay constant (in e-/cm²)
    returns polarization as a fraction (0..1)
    """
    # If dose is effectively zero, return pmax
    if dose <= 1e-12:
        return pmax
    else:
        return pmax * math.exp(-dose / phi)

class Simulation:
    def __init__(
        self,
        beam_current,       # in A
        time_step,          # in s
        beam_area,          # in cm²
        microwave_frequency=140.1,
        pmax=0.95,          # e.g. 95%
        phi=25.6E15 * 1.13,   # from victoria's thesis (page 88). the raster area was assumed to be 0.6 cm 
        trip_rate_per_hour=12,
        trip_duration_min=(20, 300),
        recovery_time_constant=300
    ):
        """
        :param beam_current: initial beam current in A
        :param time_step: time step in seconds
        :param beam_area: cross-sectional area in cm²
        :param microwave_frequency: optional effect each step
        :param pmax: max polarization (fraction, 0..1)
        :param phi: dose-based decay constant (e-/cm²)
        :param trip_rate_per_hour: approximate random beam trips/hour
        :param trip_duration_min: (min_sec, max_sec) for each random trip
        """
        # Store parameters
        self.beam_current = beam_current
        self.time_step = time_step
        self.beam_area = beam_area
        self.microwave_frequency = microwave_frequency
        self.pmax = 0.95
        self.phi = 25.6E15 * 1.13
        self.recovery_time_constant = recovery_time_constant

        # Simulation state
        self.accumulated_dose = 0.0   # in e-/cm²
        self.polarization = pmax      # initial pol
        self.time_elapsed = 0.0       # in seconds

        # Random beam trip logic
        self.in_trip = False
        self.trip_start = 0.0
        self.trip_duration = 0.0
        self.min_trip_duration, self.max_trip_duration = trip_duration_min
        self.trip_prob_per_step = trip_rate_per_hour / 3600.0

        print(f"[DEBUG] In __init__ => pmax={pmax}, phi={phi}, beam_current={beam_current}, beam_area={beam_area}")

    def step(self, action=None):
        """
        Perform one simulation step of length self.time_step.
        Optionally update parameters via an 'action' dict, e.g.:
          {'beam_current': 2e-9, 'microwave_frequency': 139.5}
        """
        # 1. RL/programmatic updates
        if action:
            if 'beam_current' in action:
                self.beam_current = action['beam_current']
            if 'microwave_frequency' in action:
                self.microwave_frequency = action['microwave_frequency']

        # 2. Beam trip logic
        if self.in_trip:
            # If the trip duration is over, restore beam
            if (self.time_elapsed - self.trip_start) > self.trip_duration:
                self.in_trip = False
                current_beam = 0.0
            else:
                current_beam = 0.0
        else:
            # Probability of a new trip
            p_trip = self.trip_prob_per_step * self.time_step
            if random.random() < p_trip:
                self.in_trip = True
                self.trip_start = self.time_elapsed
                self.trip_duration = random.uniform(self.min_trip_duration, self.max_trip_duration)
                current_beam = 0.0
            else:
                current_beam = self.beam_current

        dDose = 0.0
        if current_beam > 0.0:
            dDose = (current_beam * self.time_step) / (ELECTRON_CHARGE * self.beam_area)
            self.accumulated_dose += dDose

            base_pol = single_exponential_polarization(
                self.accumulated_dose,
                self.pmax,
                self.phi
            )
            
        else:  # no beam, polarization will increase slightly
            previous_pol = self.polarization
            delta_pol = (self.pmax - previous_pol) * (1.0 - math.exp(-self.time_step / self.recovery_time_constant))
            base_pol = previous_pol + 0.01*delta_pol

        # 5. Optional microwave effect
        #    e.g. small linear shift each step
        # If the accumulated dose is above 1E15, do not apply microwave adjustments.
        if self.accumulated_dose > 1E15:
            microwave_effect = 0.0
        else:
           # Lorentzian resonance parameters
            resonance_center = 140.1   # GHz, center frequency of resonance
            resonance_width = 0.03       # GHz, how wide the resonance peak is
            resonance_strength = 0.3     # Maximum polarization loss outside resonance
            
            freq_diff = self.microwave_frequency - resonance_center
            microwave_effect = -resonance_strength * (freq_diff**2 / (freq_diff**2 + resonance_width**2))

        # Debug prints
        print("=== Simulation Debug ===")
        print(f"  time_elapsed     = {self.time_elapsed} s")
        print(f"  current_beam     = {current_beam} A")
        print(f"  dDose            = {dDose} e-/cm²")
        print(f"  accumulated_dose = {self.accumulated_dose} e-/cm²")
        print(f"  base_pol (no mw) = {base_pol}")
        print(f"  microwave_effect = {microwave_effect}")

        # Combine
        self.polarization = base_pol + microwave_effect
        self.polarization = max(0.0, min(1.0, self.polarization))
        print(f"  final pol        = {self.polarization}")
        print("=== End Debug ===\n")

        # 6. Advance time
        self.time_elapsed += self.time_step

        # Return step data
        return {
            "time": self.time_elapsed,
            "polarization": self.polarization,
            "accumulated_dose": self.accumulated_dose,
            "beam_current": current_beam,
            "in_trip": self.in_trip,
            "microwave_frequency": self.microwave_frequency
        }

    def reset(self):
        """
        Reset simulation to initial conditions.
        """
        self.accumulated_dose = 0.0
        self.polarization = self.pmax
        self.time_elapsed = 0.0
        self.in_trip = False
        self.trip_start = 0.0
        self.trip_duration = 0.0
        print("[DEBUG] Simulation reset => dose=0, pol=pmax\n")
