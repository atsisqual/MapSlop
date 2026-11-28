"""Acceptance of actual browser driving, not a vehicle safety certification."""
import math

def evaluate_drive(baseline,candidate,target):
    fast=target==14.0
    limits={"surface_window_0_2s":8.0 if fast else 2.0,
            "surface_raw":80.0 if fast else None,
            "straight_roll_max_degrees":1.0}
    checks={};values={}
    def number(v):
        return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) and v>=0
    def metric(d,key):
        v=d.get("vertical_metrics",{}).get(key)
        return v.get("max_m_s2") if isinstance(v,dict) else v
    checks["same_reviewed_route"]=bool(baseline.get("route")==candidate.get("route") and baseline.get("route",{}).get("way")==149303998 and baseline.get("route",{}).get("name")=="Rua das Bouças")
    checks["candidate_completed"]=bool(candidate.get("success") and candidate.get("progress_m",0)>=104 and candidate.get("distance_m",0)>=104 and candidate.get("collisions")==0)
    checks["baseline_comparable"]=bool(baseline.get("success") and baseline.get("progress_m",0)>=104 and baseline.get("collisions")==0)
    if fast:
        checks["same_curvature_speed_plan"]=bool(baseline.get("speed_policy")==candidate.get("speed_policy")=="curvature_braking_envelope_v1" and baseline.get("speed_plan") and baseline.get("speed_plan")==candidate.get("speed_plan"))
        for label,d in (("baseline",baseline),("candidate",candidate)):
            v=d.get("lateral_acceleration_window_0_2s_max_m_s2")
            checks[label+"_lateral_limit"]=bool(d.get("lateral_target_limit_m_s2")==4 and number(v) and v<=4.5)
    for label,d in (("baseline",baseline),("candidate",candidate)):
        if fast:
            rows=d.get("speed_tracking_segments",[])
            checks[label+"_speed"]=bool(d.get("target_speed_m_s")==target and len(rows)==21 and all(
                row.get("start_m")==5*i and row.get("end_m")==min(104,5*(i+1))
                and row.get("samples",0)>=5 and row.get("covered_m",0)>=.7*(row["end_m"]-row["start_m"])
                and number(row.get("mean_speed_ratio")) and row["mean_speed_ratio"]>=.9
                for i,row in enumerate(rows)))
        else:
            checks[label+"_speed"]=bool(d.get("target_speed_m_s")==target and number(d.get("max_speed_m_s")) and d["max_speed_m_s"]>=.9*target and d.get("at_target_speed_samples",0)>=60)
        v=d.get("vertical_metrics",{})
        checks[label+"_sample_count"]=bool(v.get("straight_roll_samples",0)>=30 and v.get("surface_window_0_2s",{}).get("samples",0)>=60 and v.get("surface_raw",{}).get("samples",0)>=60)
    for key,limit in limits.items():
        b,c=metric(baseline,key),metric(candidate,key)
        valid=number(b) and number(c)
        values[key]={"baseline":b,"candidate":c,"absolute_limit":limit}
        checks[key+"_improved"]=bool(valid and c<b)
        checks[key+"_absolute"]=bool(valid and (limit is None or c<=limit))
    return {"pass":all(checks.values()),"target_speed_m_s":target,"checks":checks,"metrics":values,
            "failed_checks":[k for k,v in checks.items() if not v],
            "speed_tracking_segments":{k:v.get("speed_tracking_segments",[]) for k,v in (("baseline",baseline),("candidate",candidate))},
            "baseline_partial":not bool(baseline.get("success")),"baseline_progress_m":baseline.get("progress_m"),
            "candidate_progress_m":candidate.get("progress_m")}
