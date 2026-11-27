import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from road_drive_acceptance import evaluate_drive

def drive(target,window,raw,roll,complete=True):
    return dict(route={"way":149303998,"name":"Rua das Bouças"},success=complete,progress_m=104 if complete else 85,
                distance_m=104.2 if complete else 86,collisions=0,target_speed_m_s=target,max_speed_m_s=target,
                at_target_speed_samples=120,speed_policy='curvature_braking_envelope_v1',speed_plan=[{'station_m':0,'command_m_s':14}],lateral_target_limit_m_s2=4,lateral_acceleration_window_0_2s_max_m_s2=3.8,vertical_metrics={
                    "surface_window_0_2s":{"max_m_s2":window,"samples":100},
                    "surface_raw":{"max_m_s2":raw,"samples":100},
                    "straight_roll_max_degrees":roll,"straight_roll_samples":34})

class DriveAcceptanceTests(unittest.TestCase):
    def test_low_speed_requires_absolute_and_relative(self):
        b=drive(5.5,4.99,27.6,2.81)
        self.assertTrue(evaluate_drive(b,drive(5.5,1.9,20,.8),5.5)["pass"])
        self.assertFalse(evaluate_drive(b,drive(5.5,2.1,20,.8),5.5)["pass"])
        self.assertFalse(evaluate_drive(b,drive(5.5,1.9,28,.8),5.5)["pass"])
    def test_high_speed_requires_both_complete(self):
        b=drive(14,26.6,1044,11.4)
        self.assertTrue(evaluate_drive(b,drive(14,7.9,79,.8),14)["pass"])
        self.assertFalse(evaluate_drive(drive(14,26.6,1044,11.4,False),drive(14,7.9,79,.8),14)["pass"])
        self.assertFalse(evaluate_drive(b,drive(14,7.9,79,.8,False),14)["pass"])
        self.assertFalse(evaluate_drive(b,drive(14,11,141,.15),14)["pass"])
    def test_speed_and_missing_metrics_fail(self):
        b=drive(14,26.6,1044,11.4);c=drive(14,7.9,79,.8)
        c["at_target_speed_samples"]=59
        self.assertFalse(evaluate_drive(b,c,14)["pass"])
        self.assertFalse(evaluate_drive(b,{},14)["pass"])

    def test_lateral_limit_and_same_plan(self):
        b=drive(14,26.6,1044,11.4);c=drive(14,7.9,79,.8)
        c["lateral_acceleration_window_0_2s_max_m_s2"]=4.6
        self.assertFalse(evaluate_drive(b,c,14)["pass"])
        c["lateral_acceleration_window_0_2s_max_m_s2"]=3.8
        c["speed_plan"]=[{"station_m":0,"command_m_s":12}]
        self.assertFalse(evaluate_drive(b,c,14)["pass"])
