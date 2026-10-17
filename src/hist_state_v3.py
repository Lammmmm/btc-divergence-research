"""Offline specification of v3 display coordinates; not a Pine interpreter."""
import math

def neutral_score(history):
    values=[float(x) for x in history if x is not None and math.isfinite(x)]
    if not values or max(values)==min(values):return 50.0
    return max(10.0,min(90.0,10+80*(values[-1]-min(values))/(max(values)-min(values))))

def coordinates(history, active_direction=0, preview_direction=0):
    if active_direction==1:return 0.0,'yellow'
    if active_direction==-1:return 100.0,'blue'
    if preview_direction==1:return 5.0,'gray'
    if preview_direction==-1:return 95.0,'gray'
    return neutral_score(history),'gray'
